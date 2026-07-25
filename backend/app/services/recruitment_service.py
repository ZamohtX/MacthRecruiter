from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import ApplicationStatus
from app.repositories.job_repository import JobRepository
from app.schemas.job import CandidateSummaryResponse
from app.services.soft_skills_service import SoftSkillsService


class RecruitmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.job_repo = JobRepository(db)
        self.soft_skills_service = SoftSkillsService(db)

    async def get_job_candidates(
        self,
        job_id: UUID,
        min_fit_score: float | None = None,
        status_filter: ApplicationStatus | None = None,
        limit: int | None = None,
        sort_desc: bool = True,
    ) -> list[CandidateSummaryResponse]:
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job with ID {job_id} not found")

        applications = await self.job_repo.get_job_applications(job_id)
        summaries = []

        for app in applications:
            if status_filter and app.status != status_filter:
                continue

            c_scores = await self.soft_skills_service.get_user_soft_skills_profile(app.candidate_id)
            has_completed = len(c_scores) > 0

            fit_score = None
            if has_completed:
                impact = await self.soft_skills_service.calculate_impact_analysis(
                    job_id=job_id, candidate_id=app.candidate_id
                )
                fit_score = impact.fit_score

            # Filter by minimum fit score if specified
            if min_fit_score is not None:
                if fit_score is None or fit_score < min_fit_score:
                    continue

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

        # Sort candidates by fit_score (highest fit score first by default)
        if sort_desc:
            summaries.sort(key=lambda c: c.fit_score if c.fit_score is not None else -1.0, reverse=True)
        else:
            summaries.sort(key=lambda c: c.fit_score if c.fit_score is not None else 101.0)

        # Limit results if limit query parameter is provided
        if limit is not None and limit > 0:
            summaries = summaries[:limit]

        return summaries
