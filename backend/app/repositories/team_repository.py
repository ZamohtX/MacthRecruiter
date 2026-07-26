from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.team import Team, TeamInviteToken, TeamMember


class TeamRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, team_id: UUID) -> Team | None:
        stmt = select(Team).options(selectinload(Team.members).selectinload(TeamMember.user)).where(Team.id == team_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_team(self, name: str, owner_id: UUID) -> Team:
        team = Team(name=name, owner_id=owner_id)
        self.db.add(team)
        await self.db.commit()
        await self.db.refresh(team)
        return team

    async def add_member(self, team_id: UUID, user_id: UUID) -> TeamMember:
        # Check if already member
        stmt = select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        member = TeamMember(team_id=team_id, user_id=user_id)
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def get_invite_token(self, token_str: str) -> TeamInviteToken | None:
        stmt = select(TeamInviteToken).where(
            TeamInviteToken.token == token_str,
            TeamInviteToken.is_active.is_(True),
            or_(TeamInviteToken.expires_at.is_(None), TeamInviteToken.expires_at > datetime.now(UTC)),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_invite_token(
        self, team_id: UUID, token_str: str, expires_at: datetime | None = None
    ) -> TeamInviteToken:
        invite = TeamInviteToken(team_id=team_id, token=token_str, expires_at=expires_at)
        self.db.add(invite)
        await self.db.commit()
        await self.db.refresh(invite)
        return invite

    async def get_team_members(self, team_id: UUID) -> list[TeamMember]:
        stmt = (
            select(TeamMember)
            .options(selectinload(TeamMember.user))
            .where(TeamMember.team_id == team_id)
            .order_by(TeamMember.joined_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def is_member(self, team_id: UUID, user_id: UUID) -> bool:
        stmt = select(TeamMember.id).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_teams_for_user(self, user_id: UUID) -> list[Team]:
        """Times que a pessoa possui ou dos quais participa."""
        stmt = (
            select(Team)
            .outerjoin(TeamMember, TeamMember.team_id == Team.id)
            .where(or_(Team.owner_id == user_id, TeamMember.user_id == user_id))
            .order_by(Team.created_at.desc())
            .distinct()
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
