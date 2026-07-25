from collections import defaultdict
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.job_repository import JobRepository
from app.repositories.questionnaire_repository import QuestionnaireRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.user_repository import UserRepository
from app.schemas.job import ImpactAnalysisResponse, PostHiringSimulation
from app.schemas.team import TeamSoftSkillsProfileResponse


class SoftSkillsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.team_repo = TeamRepository(db)
        self.user_repo = UserRepository(db)
        self.job_repo = JobRepository(db)
        self.quest_repo = QuestionnaireRepository(db)

    async def get_user_soft_skills_profile(self, user_id: UUID) -> dict[str, float]:
        answers = await self.quest_repo.get_user_answers(user_id)
        if not answers:
            return {}

        dimension_totals = defaultdict(list)
        for ans in answers:
            if ans.question and ans.question.dimension:
                dimension_totals[ans.question.dimension].append(ans.score)

        profile = {}
        for dim, scores in dimension_totals.items():
            profile[dim] = round(sum(scores) / len(scores), 2)
        return profile

    async def get_team_soft_skills_profile(self, team_id: UUID) -> TeamSoftSkillsProfileResponse:
        team = await self.team_repo.get_by_id(team_id)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team with ID {team_id} not found",
            )

        members = await self.team_repo.get_team_members(team_id)
        if not members:
            return TeamSoftSkillsProfileResponse(
                team_id=team_id,
                team_name=team.name,
                member_count=0,
                dimension_scores={},
            )

        member_ids = [m.user_id for m in members]
        answers = await self.quest_repo.get_users_answers(member_ids)

        dimension_totals = defaultdict(list)
        for ans in answers:
            if ans.question and ans.question.dimension:
                dimension_totals[ans.question.dimension].append(ans.score)

        dimension_scores = {}
        for dim, scores in dimension_totals.items():
            dimension_scores[dim] = round(sum(scores) / len(scores), 2)

        return TeamSoftSkillsProfileResponse(
            team_id=team_id,
            team_name=team.name,
            member_count=len(members),
            dimension_scores=dimension_scores,
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

        # Ensure candidate applied to this job
        application = await self.job_repo.get_application(job_id, candidate_id)
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate application for this job was not found",
            )

        team_profile_resp = await self.get_team_soft_skills_profile(job.team_id)
        current_team_scores = team_profile_resp.dimension_scores
        current_team_size = team_profile_resp.member_count

        candidate_scores = await self.get_user_soft_skills_profile(candidate_id)

        all_dimensions = set(current_team_scores.keys()).union(set(candidate_scores.keys()))

        new_team_size = current_team_size + 1
        simulated_scores = {}
        score_deltas = {}
        gaps_filled = []
        overlaps = []

        total_complementarity = 0.0
        dim_count = len(all_dimensions) or 1

        for dim in all_dimensions:
            c_score = candidate_scores.get(dim, 0.0)
            t_score = current_team_scores.get(dim, 0.0)

            if current_team_size > 0:
                sim_score = round(((t_score * current_team_size) + c_score) / new_team_size, 2)
            else:
                sim_score = c_score

            delta = round(sim_score - t_score, 2)

            simulated_scores[dim] = sim_score
            score_deltas[dim] = delta

            # Gaps filled: team score is relatively low (<3.5) and candidate is stronger
            if t_score < 3.5 and c_score > t_score:
                gaps_filled.append(dim)
                total_complementarity += c_score - t_score
            elif c_score >= 4.0 and t_score >= 4.0:
                overlaps.append(dim)
            else:
                # Neutral or balanced contribution
                total_complementarity += max(0, c_score - t_score) * 0.5

        # Fit score scaling (0 to 100)
        fit_score = min(100.0, round(50.0 + (total_complementarity / dim_count) * 20.0, 1))

        simulation = PostHiringSimulation(
            current_team_size=current_team_size,
            new_team_size=new_team_size,
            current_team_scores=current_team_scores,
            simulated_team_scores=simulated_scores,
            score_deltas=score_deltas,
            gaps_filled=gaps_filled,
            overlaps=overlaps,
        )

        return ImpactAnalysisResponse(
            job_id=job_id,
            candidate_id=candidate_id,
            candidate_name=candidate.name,
            candidate_scores=candidate_scores,
            current_team_scores=current_team_scores,
            simulation=simulation,
            fit_score=fit_score,
        )
