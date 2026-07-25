from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import ApplicationStatus, CandidateApplication, Job


class JobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, job_id: UUID) -> Job | None:
        stmt = (
            select(Job)
            .options(selectinload(Job.team), selectinload(Job.questionnaire))
            .where(Job.id == job_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_job(
        self,
        title: str,
        team_id: UUID,
        questionnaire_id: UUID,
        description: str | None = None,
    ) -> Job:
        job = Job(
            title=title,
            team_id=team_id,
            questionnaire_id=questionnaire_id,
            description=description,
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def create_application(
        self, job_id: UUID, candidate_id: UUID
    ) -> CandidateApplication:
        stmt = select(CandidateApplication).where(
            CandidateApplication.job_id == job_id,
            CandidateApplication.candidate_id == candidate_id,
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        app = CandidateApplication(
            job_id=job_id, candidate_id=candidate_id, status=ApplicationStatus.APPLIED
        )
        self.db.add(app)
        await self.db.commit()
        await self.db.refresh(app)
        return app

    async def get_application(
        self, job_id: UUID, candidate_id: UUID
    ) -> CandidateApplication | None:
        stmt = (
            select(CandidateApplication)
            .options(
                selectinload(CandidateApplication.candidate),
                selectinload(CandidateApplication.job),
            )
            .where(
                CandidateApplication.job_id == job_id,
                CandidateApplication.candidate_id == candidate_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_job_applications(self, job_id: UUID) -> list[CandidateApplication]:
        stmt = (
            select(CandidateApplication)
            .options(selectinload(CandidateApplication.candidate))
            .where(CandidateApplication.job_id == job_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_application_status(
        self, application: CandidateApplication, status: ApplicationStatus
    ) -> CandidateApplication:
        application.status = status
        await self.db.commit()
        await self.db.refresh(application)
        return application
