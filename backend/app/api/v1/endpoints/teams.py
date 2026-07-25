import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.team_repository import TeamRepository
from app.schemas.team import (
    TeamCreate,
    TeamInviteCreateResponse,
    TeamResponse,
    TeamSoftSkillsProfileResponse,
)
from app.services.soft_skills_service import SoftSkillsService

router = APIRouter()


@router.post("", response_model=TeamResponse, status_code=201)
async def create_team(
    payload: TeamCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team_repo = TeamRepository(db)
    team = await team_repo.create_team(name=payload.name, owner_id=current_user.id)
    # Add owner as first member
    await team_repo.add_member(team.id, current_user.id)
    return team


@router.post("/{id}/invites", response_model=TeamInviteCreateResponse, status_code=201)
async def create_team_invite(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team_repo = TeamRepository(db)
    team = await team_repo.get_by_id(id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Team with ID {id} not found"
        )

    token_str = secrets.token_urlsafe(32)
    invite = await team_repo.create_invite_token(team_id=id, token_str=token_str)
    invite_url = f"/teams/{id}/invites?token={token_str}"

    return TeamInviteCreateResponse(
        invite_token=invite.token, invite_url=invite_url, expires_at=invite.expires_at
    )


@router.get("/{id}/soft-skills-profile", response_model=TeamSoftSkillsProfileResponse)
async def get_team_soft_skills_profile(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    soft_skills_service = SoftSkillsService(db)
    return await soft_skills_service.get_team_soft_skills_profile(id)
