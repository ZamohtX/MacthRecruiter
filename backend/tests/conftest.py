import asyncio
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.deps import get_db
from app.core.security import create_access_token
from app.db.base import Base
from app.main import app
from app.models.user import User, UserRole

# Use in-memory SQLite for fast isolated testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def recruiter_user(db_session: AsyncSession) -> User:
    user = User(
        email="recruiter@example.com",
        name="Recruiter User",
        role=UserRole.RECRUITER,
        google_id="recruiter_google_id",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def authenticated_client(
    async_client: AsyncClient, recruiter_user: User
) -> AsyncClient:
    token = create_access_token(subject=str(recruiter_user.id))
    async_client.headers.update({"Authorization": f"Bearer {token}"})
    return async_client


@pytest.fixture
async def candidate_user(db_session: AsyncSession) -> User:
    user = User(
        email="candidate@example.com",
        name="Candidate User",
        role=UserRole.CANDIDATE,
        google_id="candidate_google_id",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
