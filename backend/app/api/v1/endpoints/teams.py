import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.team import Team
from app.models.user import User
from app.repositories.team_repository import TeamRepository
from app.schemas.team import (
    TeamCreate,
    TeamDiagnosticStatusResponse,
    TeamGapAnalysisResponse,
    TeamInviteCreateResponse,
    TeamResponse,
    TeamSoftSkillsProfileResponse,
)
from app.services.soft_skills_service import SoftSkillsService

router = APIRouter()

INVITE_TTL_DAYS = 30


async def _get_team_or_404(team_repo: TeamRepository, team_id: UUID) -> Team:
    team = await team_repo.get_by_id(team_id)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team with ID {team_id} not found")
    return team


async def _ensure_owner(team_repo: TeamRepository, team_id: UUID, user: User) -> Team:
    """Ações administrativas do time (convite, diagnóstico agregado) são do dono."""
    team = await _get_team_or_404(team_repo, team_id)
    if team.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o responsável pelo time pode executar esta ação.",
        )
    return team


async def _ensure_member_or_owner(team_repo: TeamRepository, team_id: UUID, user: User) -> Team:
    team = await _get_team_or_404(team_repo, team_id)
    if team.owner_id == user.id or await team_repo.is_member(team_id, user.id):
        return team
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Você não faz parte deste time.",
    )


@router.post("", response_model=TeamResponse, status_code=201)
async def create_team(
    payload: TeamCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cria o time. Quem cria fica como **responsável, não integrante**.

    O recrutador normalmente é de RH e não faz parte do time diagnosticado —
    incluí-lo contaminaria a média com o perfil de alguém que não convive com o
    problema que a vaga vai resolver. Quando quem abre a vaga é o próprio gestor
    do squad, ele entra pelo mesmo link de convite dos demais.
    """
    team_repo = TeamRepository(db)
    return await team_repo.create_team(name=payload.name, owner_id=current_user.id)


@router.get("", response_model=list[TeamResponse])
async def list_my_teams(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Times que a pessoa autenticada possui ou dos quais participa."""
    team_repo = TeamRepository(db)
    return await team_repo.list_teams_for_user(current_user.id)


@router.post("/{id}/invites", response_model=TeamInviteCreateResponse, status_code=201)
async def create_team_invite(
    id: UUID,
    expires_in_days: int = Query(INVITE_TTL_DAYS, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team_repo = TeamRepository(db)
    await _ensure_owner(team_repo, id, current_user)

    token_str = secrets.token_urlsafe(32)
    invite = await team_repo.create_invite_token(
        team_id=id,
        token_str=token_str,
        expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
    )
    invite_url = f"/teams/{id}/invites?token={token_str}"

    return TeamInviteCreateResponse(invite_token=invite.token, invite_url=invite_url, expires_at=invite.expires_at)


@router.get("/{id}/soft-skills-profile", response_model=TeamSoftSkillsProfileResponse)
async def get_team_soft_skills_profile(
    id: UUID,
    questionnaire_id: UUID | None = Query(
        None, description="Restringe o cálculo a um instrumento específico. Padrão: todas as respostas."
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Etapa 1 — perfil comportamental agregado do time."""
    team_repo = TeamRepository(db)
    await _ensure_member_or_owner(team_repo, id, current_user)

    soft_skills_service = SoftSkillsService(db)
    return await soft_skills_service.get_team_soft_skills_profile(id, questionnaire_id)


@router.get("/{id}/diagnostic-status", response_model=TeamDiagnosticStatusResponse)
async def get_team_diagnostic_status(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Quem do time já respondeu o diagnóstico e se a vaga pode ser aberta."""
    team_repo = TeamRepository(db)
    await _ensure_owner(team_repo, id, current_user)

    soft_skills_service = SoftSkillsService(db)
    return await soft_skills_service.get_team_diagnostic_status(id)


@router.get("/{id}/gap-analysis", response_model=TeamGapAnalysisResponse)
async def get_team_gap_analysis(
    id: UUID,
    questionnaire_id: UUID | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Etapa 2 — converte as lacunas do time no perfil-alvo ponderado da vaga."""
    team_repo = TeamRepository(db)
    await _ensure_owner(team_repo, id, current_user)

    soft_skills_service = SoftSkillsService(db)
    return await soft_skills_service.get_gap_analysis(id, questionnaire_id)
