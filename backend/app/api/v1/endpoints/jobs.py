from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.job_repository import JobRepository
from app.repositories.questionnaire_repository import QuestionnaireRepository
from app.schemas.job import (
    CandidateSummaryResponse,
    ImpactAnalysisResponse,
    JobCreate,
    JobResponse,
)
from app.schemas.questionnaire import QuestionnaireSubmitRequest
from app.services.recruitment_service import RecruitmentService
from app.services.soft_skills_service import SoftSkillsService

router = APIRouter()


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(
    payload: JobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job_repo = JobRepository(db)
    return await job_repo.create_job(
        title=payload.title,
        team_id=payload.team_id,
        questionnaire_id=payload.questionnaire_id,
        description=payload.description,
    )


@router.post("/{job_id}/apply", status_code=201)
async def apply_to_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job_repo = JobRepository(db)
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )
    application = await job_repo.create_application(
        job_id=job_id, candidate_id=current_user.id
    )
    return {"message": "Applied successfully", "application_id": str(application.id)}


@router.post("/{job_id}/answers", status_code=200)
async def submit_questionnaire_answers(
    job_id: UUID,
    payload: QuestionnaireSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job_repo = JobRepository(db)
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )

    quest_repo = QuestionnaireRepository(db)
    saved_answers = []
    for ans in payload.answers:
        res = await quest_repo.save_answer(
            user_id=current_user.id, question_id=ans.question_id, score=ans.score
        )
        saved_answers.append(res)

    # Update application status if applicable
    app = await job_repo.get_application(job_id, current_user.id)
    if app:
        from app.models.job import ApplicationStatus

        await job_repo.update_application_status(
            app, ApplicationStatus.SOFT_SKILLS_COMPLETED
        )

    return {
        "message": "Answers submitted successfully",
        "total_answers": len(saved_answers),
    }


@router.get("/{job_id}/candidates", response_model=list[CandidateSummaryResponse])
async def get_job_candidates(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    recruitment_service = RecruitmentService(db)
    return await recruitment_service.get_job_candidates(job_id)


@router.post(
    "/{job_id}/candidates/{candidate_id}/impact-analysis",
    response_model=ImpactAnalysisResponse,
)
async def get_candidate_impact_analysis(
    job_id: UUID,
    candidate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    soft_skills_service = SoftSkillsService(db)
    return await soft_skills_service.calculate_impact_analysis(
        job_id=job_id, candidate_id=candidate_id
    )
