from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import ApplicationStatus, CandidateApplication, Job
from app.models.questionnaire import AssessmentAnswer
from app.models.user import User
from app.repositories.job_repository import JobRepository
from app.repositories.questionnaire_repository import QuestionnaireRepository
from app.repositories.team_repository import TeamRepository
from app.schemas.job import CandidateSummaryResponse, JobDetailResponse
from app.services.assessment_service import profile_from_answers
from app.services.soft_skills_service import SoftSkillsService


class RecruitmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.job_repo = JobRepository(db)
        self.team_repo = TeamRepository(db)
        self.quest_repo = QuestionnaireRepository(db)
        self.soft_skills_service = SoftSkillsService(db)

    # ------------------------------------------------------------------
    # Autorização
    # ------------------------------------------------------------------

    async def get_job_or_404(self, job_id: UUID) -> Job:
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job with ID {job_id} not found")
        return job

    async def ensure_job_owner(self, job_id: UUID, user: User) -> Job:
        """Dados de candidatos só podem ser vistos por quem é dono do time da vaga.

        Sem esta checagem qualquer pessoa autenticada consegue ler o perfil
        comportamental de qualquer candidato de qualquer empresa.
        """
        job = await self.get_job_or_404(job_id)
        team = await self.team_repo.get_by_id(job.team_id)
        if team is None or team.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas o responsável pelo time desta vaga pode acessar este recurso.",
            )
        return job

    # ------------------------------------------------------------------
    # Vagas
    # ------------------------------------------------------------------

    async def create_job(
        self, user: User, title: str, team_id: UUID, questionnaire_id: UUID | None, description: str | None
    ) -> Job:
        team = await self.team_repo.get_by_id(team_id)
        if not team:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team with ID {team_id} not found")
        if team.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas o responsável pelo time pode abrir vagas para ele.",
            )

        if questionnaire_id is None:
            default = await self.quest_repo.get_default()
            if default is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Nenhum questionário padrão cadastrado. Informe questionnaire_id "
                        "ou rode o seed do banco (`make seed`)."
                    ),
                )
            questionnaire_id = default.id
        elif await self.quest_repo.get_by_id(questionnaire_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Questionnaire with ID {questionnaire_id} not found",
            )

        return await self.job_repo.create_job(
            title=title, team_id=team_id, questionnaire_id=questionnaire_id, description=description
        )

    async def get_job_detail(self, job_id: UUID) -> JobDetailResponse:
        job = await self.get_job_or_404(job_id)
        applications = await self.job_repo.get_job_applications(job_id)
        team_profile = await self.soft_skills_service.load_team_profile(job.team_id, job.questionnaire_id)

        return JobDetailResponse(
            id=job.id,
            team_id=job.team_id,
            questionnaire_id=job.questionnaire_id,
            title=job.title,
            description=job.description,
            created_at=job.created_at,
            team_name=job.team.name if job.team else "",
            questionnaire_title=job.questionnaire.title if job.questionnaire else "",
            application_count=len(applications),
            team_assessment_ready=team_profile.respondent_count > 0,
        )

    async def list_jobs_for_user(self, user: User) -> list[Job]:
        teams = await self.team_repo.list_teams_for_user(user.id)
        owned_team_ids = [t.id for t in teams if t.owner_id == user.id]
        return await self.job_repo.list_jobs_for_teams(owned_team_ids)

    # ------------------------------------------------------------------
    # Candidatos
    # ------------------------------------------------------------------

    async def update_application_status(
        self, job_id: UUID, candidate_id: UUID, new_status: ApplicationStatus
    ) -> CandidateApplication:
        application = await self.job_repo.get_application(job_id, candidate_id)
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate application for this job was not found",
            )
        return await self.job_repo.update_application_status(application, new_status)

    async def get_job_candidates(
        self,
        job_id: UUID,
        min_fit_score: float | None = None,
        status_filter: ApplicationStatus | None = None,
        limit: int | None = None,
        sort_desc: bool = True,
    ) -> list[CandidateSummaryResponse]:
        job = await self.get_job_or_404(job_id)
        applications = await self.job_repo.get_job_applications(job_id)

        if status_filter:
            applications = [a for a in applications if a.status == status_filter]
        if not applications:
            return []

        # O perfil do time é o mesmo para todos os candidatos da vaga: carregar
        # uma vez em vez de uma vez por candidato.
        team_profile = await self.soft_skills_service.load_team_profile(job.team_id, job.questionnaire_id)

        candidate_ids = [a.candidate_id for a in applications]
        all_answers = await self.quest_repo.get_users_answers(candidate_ids)

        by_candidate: dict[UUID, list[AssessmentAnswer]] = {cid: [] for cid in candidate_ids}
        for answer in all_answers:
            if answer.question and answer.question.questionnaire_id == job.questionnaire_id:
                by_candidate[answer.user_id].append(answer)

        summaries: list[CandidateSummaryResponse] = []
        for application in applications:
            scores = profile_from_answers(by_candidate.get(application.candidate_id, []))
            has_completed = bool(scores)

            fit_score = None
            supplementary = None
            verdict = None
            gaps_filled: list[str] = []

            if has_completed:
                impact = self.soft_skills_service.build_impact_response(
                    job_id=job_id,
                    candidate_id=application.candidate_id,
                    candidate_name=application.candidate.name if application.candidate else "Desconhecido",
                    candidate_scores=scores,
                    team_profile=team_profile,
                )
                fit_score = impact.fit_score
                supplementary = impact.supplementary_fit_index
                verdict = impact.verdict
                gaps_filled = impact.simulation.gaps_filled

            if min_fit_score is not None and (fit_score is None or fit_score < min_fit_score):
                continue

            summaries.append(
                CandidateSummaryResponse(
                    application_id=application.id,
                    candidate_id=application.candidate_id,
                    candidate_name=application.candidate.name if application.candidate else "Desconhecido",
                    candidate_email=application.candidate.email if application.candidate else "",
                    status=application.status,
                    applied_at=application.applied_at,
                    soft_skills_completed=has_completed,
                    candidate_scores=scores if has_completed else None,
                    fit_score=fit_score,
                    supplementary_fit_index=supplementary,
                    verdict=verdict,
                    gaps_filled=gaps_filled,
                )
            )

        # Quem ainda não respondeu o questionário fica no fim da lista em ambas as
        # ordenações: não há fit medido, então não deve ocupar o topo.
        summaries.sort(
            key=lambda c: (c.fit_score is None, -(c.fit_score or 0.0) if sort_desc else (c.fit_score or 0.0))
        )

        if limit is not None and limit > 0:
            summaries = summaries[:limit]

        return summaries
