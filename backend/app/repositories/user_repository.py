from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: UUID) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_google_id(self, google_id: str) -> User | None:
        stmt = select(User).where(User.google_id == google_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, email: str, name: str, role: UserRole, google_id: str | None = None) -> User:
        user = User(email=email, name=name, role=role, google_id=google_id)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_role(self, user: User, role: UserRole) -> User:
        user.role = role
        await self.db.commit()
        await self.db.refresh(user)
        return user
