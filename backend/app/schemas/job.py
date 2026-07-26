from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.job import ApplicationStatus


class JobCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    team_id: UUID
    # Opcional: sem valor, a vaga usa o instrumento padrão da plataforma — o mesmo
    # que o time respondeu, garantindo que os dois perfis sejam comparáveis.
    questionnaire_id: UUID | None = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    questionnaire_id: UUID
    title: str
    description: str | None = None
    created_at: datetime


class JobDetailResponse(JobResponse):
    team_name: str
    questionnaire_title: str
    application_count: int = 0
    team_assessment_ready: bool = False


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    candidate_id: UUID
    status: ApplicationStatus
    applied_at: datetime


class PostHiringSimulation(BaseModel):
    current_team_size: int
    new_team_size: int
    current_team_scores: dict[str, float]
    simulated_team_scores: dict[str, float]
    score_deltas: dict[str, float]  # simulated - current
    gaps_filled: list[str]  # lacunas do time que o candidato cobre
    gaps_missed: list[str]  # lacunas que continuam descobertas após a contratação
    overlaps: list[str]  # dimensões em que o candidato apenas repete força já existente


class DimensionInsightResponse(BaseModel):
    dimension: str
    team_score: float
    candidate_score: float
    simulated_score: float
    delta: float
    status: str  # GAP | ADEQUATE | STRENGTH
    # FILLS_GAP | PARTIAL_LIFT | REDUNDANT | AGGRAVATES_GAP | DILUTES_STRENGTH | NEUTRAL
    contribution: str
    explanation: str


class ImpactAnalysisResponse(BaseModel):
    job_id: UUID
    candidate_id: UUID
    candidate_name: str
    candidate_scores: dict[str, float]
    current_team_scores: dict[str, float]
    simulation: PostHiringSimulation

    # Ranking do candidato por complementaridade (0–100).
    fit_score: float
    # Alias explícito de `fit_score`; nomeado para contrastar com o índice abaixo.
    complementary_fit_score: float
    # Semelhança do candidato com o time (0–100). Valor alto com fit complementar
    # baixo é exatamente o caso de "fit suplementar em excesso" que se quer evitar.
    supplementary_fit_index: float

    gap_coverage: float | None = None
    balance_gain: float | None = None
    redundancy: float | None = None

    verdict: str
    risk_flags: list[str] = Field(default_factory=list)
    insights: list[DimensionInsightResponse] = Field(default_factory=list)


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
    supplementary_fit_index: float | None = None
    verdict: str | None = None
    gaps_filled: list[str] = Field(default_factory=list)
