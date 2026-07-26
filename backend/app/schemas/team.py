from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    owner_id: UUID
    created_at: datetime


class TeamInviteCreateResponse(BaseModel):
    invite_token: str
    invite_url: str
    expires_at: datetime | None = None


class TeamSoftSkillsProfileResponse(BaseModel):
    team_id: UUID
    team_name: str
    member_count: int
    # Camada observável: as 10 soft skills, usadas na lacuna e no fit.
    dimension_scores: dict[str, float]
    # Camada latente: os cinco fatores Big Five de onde as competências derivam.
    trait_scores: dict[str, float] = Field(default_factory=dict)
    # Quantos integrantes efetivamente responderam o diagnóstico. Sem isso é
    # impossível distinguir "time equilibrado" de "ninguém respondeu ainda".
    respondent_count: int = 0
    completion_rate: float = 0.0
    dispersion: float = 0.0
    low_confidence: bool = True
    confidence_note: str | None = None


class TeamMemberStatusResponse(BaseModel):
    user_id: UUID
    name: str
    email: str
    joined_at: datetime
    is_owner: bool
    assessment_completed: bool
    answered_questions: int
    total_questions: int


class TeamDiagnosticStatusResponse(BaseModel):
    team_id: UUID
    team_name: str
    questionnaire_id: UUID | None
    member_count: int
    respondent_count: int
    completion_rate: float
    ready_for_job_opening: bool
    members: list[TeamMemberStatusResponse]


class DimensionGap(BaseModel):
    dimension: str
    team_score: float
    status: str  # GAP | ADEQUATE | STRENGTH
    deficit: float  # 0.0–1.0, tamanho da lacuna
    weight: float  # peso da dimensão no perfil-alvo da vaga (soma 1.0)
    members_below_threshold: int
    members_assessed: int
    rationale: str


class TeamGapAnalysisResponse(BaseModel):
    """Etapa 2 do fluxo: converte as lacunas do time no perfil-alvo da vaga."""

    team_id: UUID
    team_name: str
    member_count: int
    respondent_count: int
    low_confidence: bool
    dimensions: list[DimensionGap]
    priority_dimensions: list[str]
    strengths: list[str]
    target_profile: dict[str, float]  # nota mínima desejada por dimensão
    summary: str
