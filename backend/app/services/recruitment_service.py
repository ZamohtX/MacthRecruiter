from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.job_repository import JobRepository
from app.schemas.job import CandidateSummaryResponse
from app.services.soft_skills_service import SoftSkillsService


class RecruitmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.job_repo = JobRepository(db)
        self.soft_skills_service = SoftSkillsService(db)

    async def get_job_candidates(self, job_id: UUID) -> list[CandidateSummaryResponse]:
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with ID {job_id} not found",
            )

        applications = await self.job_repo.get_job_applications(job_id)
        summaries = []

        for app in applications:
            c_scores = await self.soft_skills_service.get_user_soft_skills_profile(
                app.candidate_id
            )
            has_completed = len(c_scores) > 0

            fit_score = None
            if has_completed:
                impact = await self.soft_skills_service.calculate_impact_analysis(
                    job_id=job_id, candidate_id=app.candidate_id
                )
                fit_score = impact.fit_score

            summaries.append(
                CandidateSummaryResponse(
                    application_id=app.id,
                    candidate_id=app.candidate_id,
                    candidate_name=app.candidate.name if app.candidate else "Unknown",
                    candidate_email=app.candidate.email if app.candidate else "",
                    status=app.status,
                    applied_at=app.applied_at,
                    soft_skills_completed=has_completed,
                    candidate_scores=c_scores if has_completed else None,
                    fit_score=fit_score,
                )
            )

        return summaries
