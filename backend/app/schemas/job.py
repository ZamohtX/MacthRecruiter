from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.job import ApplicationStatus


class JobCreate(BaseModel):
    title: str
    description: str | None = None
    team_id: UUID
    questionnaire_id: UUID


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    questionnaire_id: UUID
    title: str
    description: str | None = None
    created_at: datetime


class PostHiringSimulation(BaseModel):
    current_team_size: int
    new_team_size: int
    current_team_scores: dict[str, float]
    simulated_team_scores: dict[str, float]
    score_deltas: dict[str, float]  # simulated - current
    gaps_filled: list[
        str
    ]  # dimensions where candidate significantly boosts lower team scores
    overlaps: list[
        str
    ]  # dimensions where candidate is already similar or redundant to team high scores


class ImpactAnalysisResponse(BaseModel):
    job_id: UUID
    candidate_id: UUID
    candidate_name: str
    candidate_scores: dict[str, float]
    current_team_scores: dict[str, float]
    simulation: PostHiringSimulation
    fit_score: float  # Numerical score 0-100 representing complementary fit


class CandidateSummaryResponse(BaseModel):
    application_id: UUID
    candidate_id: UUID
    candidate_name: str
    candidate_email: str
    status: ApplicationStatus
    applied_at: datetime
    soft_skills_completed: bool
    candidate_scores: dict[str, float] | None = None
    fit_score: float | None = None
