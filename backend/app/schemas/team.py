from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TeamCreate(BaseModel):
    name: str


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
    dimension_scores: dict[str, float]
