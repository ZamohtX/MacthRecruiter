from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.soft_skills import (
    DIMENSIONS,
    MIN_CANDIDATE_FLOOR,
    MIN_RESPONDENTS_FOR_CONFIDENCE,
    SCALE_MAX,
)
from app.models.questionnaire import AssessmentAnswer
from app.models.team import Team
from app.repositories.job_repository import JobRepository
from app.repositories.questionnaire_repository import QuestionnaireRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.user_repository import UserRepository
from app.schemas.job import (
    DimensionInsightResponse,
    ImpactAnalysisResponse,
    PostHiringSimulation,
)
from app.schemas.team import (
    DimensionGap,
    TeamDiagnosticStatusResponse,
    TeamGapAnalysisResponse,
    TeamMemberStatusResponse,
    TeamSoftSkillsProfileResponse,
)
from app.services.assessment_service import profile_from_answers, trait_profile_from_answers
from app.services.fit_engine import (
    DimensionStatus,
    classify_dimension,
    deficit_weight,
    evaluate_fit,
    profile_norms,
    team_profile_dispersion,
)


def _average_profiles(profiles) -> dict[str, float]:
    """Média, dimensão a dimensão, dos perfis individuais dos integrantes.

    O perfil do time é a média das **pessoas**, não das respostas agrupadas. Com
    um instrumento de escolha forçada os dois números divergem: a pontuação de
    cada fator é normalizada contra os limites de um respondente, então somar as
    escolhas de N pessoas e normalizar uma vez só infla todos os fatores para o
    topo da escala. Além disso, mediar por pessoa dá o mesmo peso a cada
    integrante, mesmo que uns tenham respondido mais itens que outros.
    """
    answered = [p for p in profiles if p]
    if not answered:
        return {}

    keys = {key for profile in answered for key in profile}
    averaged: dict[str, float] = {}
    for key in keys:
        values = [profile[key] for profile in answered if key in profile]
        if values:
            averaged[key] = round(sum(values) / len(values), 2)
    return averaged


class TeamProfile:
    """Perfil agregado do time + metadados de confiabilidade da medida."""

    def __init__(
        self,
        team: Team,
        member_count: int,
        respondent_count: int,
        dimension_scores: dict[str, float],
        member_profiles: dict[UUID, dict[str, float]],
        trait_scores: dict[str, float] | None = None,
    ):
        self.team = team
        self.member_count = member_count
        self.respondent_count = respondent_count
        self.dimension_scores = dimension_scores
        self.member_profiles = member_profiles
        # Camada latente do time. Não entra no fit (que roda sobre competências),
        # mas é o que dá ao gestor a leitura de "que tipo de gente é este time".
        self.trait_scores = trait_scores or {}

    @property
    def completion_rate(self) -> float:
        if self.member_count <= 0:
            return 0.0
        return round(self.respondent_count / self.member_count, 2)

    @property
    def low_confidence(self) -> bool:
        return self.respondent_count < MIN_RESPONDENTS_FOR_CONFIDENCE

    @property
    def confidence_note(self) -> str | None:
        if self.respondent_count == 0:
            return (
                "Nenhum integrante respondeu ao diagnóstico. O perfil do time está vazio e "
                "qualquer comparação com candidatos é inválida."
            )
        if self.low_confidence:
            return (
                f"Apenas {self.respondent_count} integrante(s) respondeu(ram). Com menos de "
                f"{MIN_RESPONDENTS_FOR_CONFIDENCE} respondentes a média do time tem margem de erro "
                f"alta — trate o resultado como indicativo, não como medida."
            )
        return None


class SoftSkillsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.team_repo = TeamRepository(db)
        self.user_repo = UserRepository(db)
        self.job_repo = JobRepository(db)
        self.quest_repo = QuestionnaireRepository(db)

    # ------------------------------------------------------------------
    # Perfis individuais
    # ------------------------------------------------------------------

    async def get_user_soft_skills_profile(
        self, user_id: UUID, questionnaire_id: UUID | None = None
    ) -> dict[str, float]:
        if questionnaire_id is None:
            answers = await self.quest_repo.get_user_answers(user_id)
        else:
            answers = await self.quest_repo.get_user_answers_for_questionnaire(user_id, questionnaire_id)
        return profile_from_answers(answers)

    # ------------------------------------------------------------------
    # Etapa 1 — Diagnóstico do time
    # ------------------------------------------------------------------

    async def load_team_profile(self, team_id: UUID, questionnaire_id: UUID | None = None) -> TeamProfile:
        team = await self.team_repo.get_by_id(team_id)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team with ID {team_id} not found",
            )

        members = await self.team_repo.get_team_members(team_id)
        member_ids = [m.user_id for m in members]
        answers = await self.quest_repo.get_users_answers(member_ids)

        if questionnaire_id is not None:
            answers = [a for a in answers if a.question and a.question.questionnaire_id == questionnaire_id]

        by_member: dict[UUID, list[AssessmentAnswer]] = {uid: [] for uid in member_ids}
        for answer in answers:
            if answer.user_id in by_member:
                by_member[answer.user_id].append(answer)

        member_profiles = {uid: profile_from_answers(items) for uid, items in by_member.items()}
        member_traits = {uid: trait_profile_from_answers(items) for uid, items in by_member.items()}
        respondent_count = sum(1 for profile in member_profiles.values() if profile)

        return TeamProfile(
            team=team,
            member_count=len(members),
            respondent_count=respondent_count,
            dimension_scores=_average_profiles(member_profiles.values()),
            member_profiles=member_profiles,
            trait_scores=_average_profiles(member_traits.values()),
        )

    async def get_team_soft_skills_profile(
        self, team_id: UUID, questionnaire_id: UUID | None = None
    ) -> TeamSoftSkillsProfileResponse:
        profile = await self.load_team_profile(team_id, questionnaire_id)

        return TeamSoftSkillsProfileResponse(
            team_id=team_id,
            team_name=profile.team.name,
            member_count=profile.member_count,
            dimension_scores=profile.dimension_scores,
            trait_scores=profile.trait_scores,
            respondent_count=profile.respondent_count,
            completion_rate=profile.completion_rate,
            dispersion=team_profile_dispersion(profile.dimension_scores),
            low_confidence=profile.low_confidence,
            confidence_note=profile.confidence_note,
        )

    async def get_team_diagnostic_status(self, team_id: UUID) -> TeamDiagnosticStatusResponse:
        """Quem do time já respondeu — o recrutador precisa disso para saber
        quando o diagnóstico está maduro o bastante para abrir a vaga."""
        questionnaire = await self.quest_repo.get_default()
        questionnaire_id = questionnaire.id if questionnaire else None
        total_questions = len(questionnaire.questions) if questionnaire else 0

        profile = await self.load_team_profile(team_id, questionnaire_id)
        members = await self.team_repo.get_team_members(team_id)

        member_statuses: list[TeamMemberStatusResponse] = []
        for member in members:
            answered = 0
            if questionnaire_id is not None:
                answers = await self.quest_repo.get_user_answers_for_questionnaire(member.user_id, questionnaire_id)
                answered = len(answers)

            member_statuses.append(
                TeamMemberStatusResponse(
                    user_id=member.user_id,
                    name=member.user.name if member.user else "Desconhecido",
                    email=member.user.email if member.user else "",
                    joined_at=member.joined_at,
                    is_owner=member.user_id == profile.team.owner_id,
                    assessment_completed=total_questions > 0 and answered >= total_questions,
                    answered_questions=answered,
                    total_questions=total_questions,
                )
            )

        return TeamDiagnosticStatusResponse(
            team_id=team_id,
            team_name=profile.team.name,
            questionnaire_id=questionnaire_id,
            member_count=profile.member_count,
            respondent_count=profile.respondent_count,
            completion_rate=profile.completion_rate,
            ready_for_job_opening=profile.respondent_count >= MIN_RESPONDENTS_FOR_CONFIDENCE,
            members=member_statuses,
        )

    # ------------------------------------------------------------------
    # Etapa 2 — Perfil-alvo por lacuna
    # ------------------------------------------------------------------

    async def get_gap_analysis(self, team_id: UUID, questionnaire_id: UUID | None = None) -> TeamGapAnalysisResponse:
        if questionnaire_id is None:
            default = await self.quest_repo.get_default()
            questionnaire_id = default.id if default else None

        profile = await self.load_team_profile(team_id, questionnaire_id)
        scores = profile.dimension_scores

        dimensions = sorted(set(DIMENSIONS) | set(scores)) if scores else list(DIMENSIONS)
        assessed_profiles = [p for p in profile.member_profiles.values() if p]
        # Lacuna e força são relativas ao próprio perfil do time — ver
        # `fit_engine.classify_dimension`.
        norms = profile_norms(scores)

        raw_weights: dict[str, float] = {}
        gaps: list[DimensionGap] = []

        for dim in dimensions:
            team_score = scores.get(dim, 0.0)
            dim_status = classify_dimension(team_score, norms) if scores else DimensionStatus.GAP
            deficit = deficit_weight(team_score, norms) if scores else 1.0
            raw_weights[dim] = deficit

            below = sum(1 for p in assessed_profiles if p.get(dim, 0.0) < norms.center)
            assessed = sum(1 for p in assessed_profiles if dim in p)

            if not scores:
                rationale = "Time ainda não respondeu ao diagnóstico — dimensão sem medida."
            elif dim_status == DimensionStatus.GAP:
                rationale = (
                    f"Média do time em {dim} é {team_score:.1f}, abaixo do nível médio do próprio "
                    f"time ({norms.center:.1f}). {below} de {assessed} respondente(s) pontuam "
                    f"abaixo desse nível."
                )
            elif dim_status == DimensionStatus.STRENGTH:
                rationale = (
                    f"{dim} já é força consolidada do time (média {team_score:.1f}). "
                    f"Contratar mais desta competência agrega pouco à composição."
                )
            else:
                rationale = f"{dim} está em nível adequado (média {team_score:.1f}), sem urgência de reforço."

            gaps.append(
                DimensionGap(
                    dimension=dim,
                    team_score=round(team_score, 2),
                    status=dim_status,
                    deficit=round(deficit, 3),
                    weight=0.0,  # preenchido depois da normalização
                    members_below_threshold=below,
                    members_assessed=assessed,
                    rationale=rationale,
                )
            )

        # Normaliza os déficits em pesos que somam 1.0. Time sem nenhuma lacuna
        # cai para peso uniforme: não há o que priorizar por complementaridade.
        total = sum(raw_weights.values())
        for gap in gaps:
            gap.weight = round(raw_weights[gap.dimension] / total, 3) if total > 0 else round(1 / len(gaps), 3)

        gaps.sort(key=lambda g: (-g.weight, g.dimension))

        priority = [g.dimension for g in gaps if g.status == DimensionStatus.GAP]
        strengths = [g.dimension for g in gaps if g.status == DimensionStatus.STRENGTH]

        # Alvo elevado nas lacunas + piso mínimo nas demais. O piso impede que
        # uma competência seja zerada só porque o time já a tem.
        #
        # O alvo da lacuna é o ponto em que ela deixaria de ser lacuna neste time:
        # o centro do perfil mais a banda de classificação. Um alvo fixo não
        # serviria — a régua é relativa ao time.
        gap_target = min(SCALE_MAX, round(norms.center + norms.spread, 2)) if not norms.is_uniform else SCALE_MAX
        target_profile = {
            g.dimension: gap_target if g.status == DimensionStatus.GAP else MIN_CANDIDATE_FLOOR for g in gaps
        }

        if profile.respondent_count == 0:
            summary = (
                "Diagnóstico não iniciado: nenhum integrante respondeu ao questionário. "
                "Sem isso não é possível gerar o perfil-alvo por lacuna."
            )
        elif priority:
            summary = (
                f"O time tem {len(priority)} lacuna(s) comportamental(is). "
                f"Prioridade de contratação: {', '.join(priority[:3])}. "
                f"Forças já cobertas: {', '.join(strengths) if strengths else 'nenhuma consolidada'}."
            )
        else:
            summary = (
                "Nenhuma lacuna comportamental identificada acima do limiar. O perfil-alvo cai "
                "para peso uniforme — priorize hard skills e o piso mínimo por competência."
            )

        return TeamGapAnalysisResponse(
            team_id=team_id,
            team_name=profile.team.name,
            member_count=profile.member_count,
            respondent_count=profile.respondent_count,
            low_confidence=profile.low_confidence,
            dimensions=gaps,
            priority_dimensions=priority,
            strengths=strengths,
            target_profile=target_profile,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Simulação pós-contratação
    # ------------------------------------------------------------------

    def build_impact_response(
        self,
        job_id: UUID,
        candidate_id: UUID,
        candidate_name: str,
        candidate_scores: dict[str, float],
        team_profile: TeamProfile,
    ) -> ImpactAnalysisResponse:
        """Monta a resposta de impacto a partir de perfis já carregados.

        Recebe o perfil do time pronto para que a listagem de candidatos calcule
        o diagnóstico do time uma única vez, em vez de uma vez por candidato.
        """
        result = evaluate_fit(
            team_scores=team_profile.dimension_scores,
            candidate_scores=candidate_scores,
            team_size=team_profile.member_count,
            respondent_count=team_profile.respondent_count,
        )

        simulation = PostHiringSimulation(
            current_team_size=team_profile.member_count,
            new_team_size=team_profile.member_count + 1,
            current_team_scores=team_profile.dimension_scores,
            simulated_team_scores=result.simulated_scores,
            score_deltas=result.score_deltas,
            gaps_filled=result.gaps_filled,
            gaps_missed=result.gaps_missed,
            overlaps=result.overlaps,
        )

        return ImpactAnalysisResponse(
            job_id=job_id,
            candidate_id=candidate_id,
            candidate_name=candidate_name,
            candidate_scores=candidate_scores,
            current_team_scores=team_profile.dimension_scores,
            simulation=simulation,
            fit_score=result.complementary_fit_score,
            complementary_fit_score=result.complementary_fit_score,
            supplementary_fit_index=result.supplementary_fit_index,
            gap_coverage=result.gap_coverage,
            balance_gain=result.balance_gain,
            redundancy=result.redundancy,
            verdict=result.verdict,
            risk_flags=result.risk_flags,
            insights=[DimensionInsightResponse(**vars(i)) for i in result.insights],
        )

    async def calculate_impact_analysis(self, job_id: UUID, candidate_id: UUID) -> ImpactAnalysisResponse:
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with ID {job_id} not found",
            )

        candidate = await self.user_repo.get_by_id(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID {candidate_id} not found",
            )

        application = await self.job_repo.get_application(job_id, candidate_id)
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate application for this job was not found",
            )

        # Time e candidato precisam ser medidos pelo mesmo instrumento, senão a
        # comparação dimensão a dimensão não tem significado.
        team_profile = await self.load_team_profile(job.team_id, job.questionnaire_id)
        candidate_scores = await self.get_user_soft_skills_profile(candidate_id, job.questionnaire_id)

        return self.build_impact_response(
            job_id=job_id,
            candidate_id=candidate_id,
            candidate_name=candidate.name,
            candidate_scores=candidate_scores,
            team_profile=team_profile,
        )
