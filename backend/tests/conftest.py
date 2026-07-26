import asyncio
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.big_five import TRAITS
from app.core.deps import get_db
from app.core.security import create_access_token
from app.db.base import Base
from app.db.seed import seed_default_questionnaire
from app.main import app
from app.models.questionnaire import Questionnaire
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
async def authenticated_client(async_client: AsyncClient, recruiter_user: User) -> AsyncClient:
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


@pytest.fixture
async def other_recruiter(db_session: AsyncSession) -> User:
    """Segundo recrutador, de outra empresa — usado para testar isolamento de dados."""
    user = User(
        email="other@example.com",
        name="Other Recruiter",
        role=UserRole.RECRUITER,
        google_id="other_google_id",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def other_recruiter_client(async_client: AsyncClient, other_recruiter: User) -> AsyncClient:
    return AsyncClient(
        transport=async_client._transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {create_access_token(subject=str(other_recruiter.id))}"},
    )


@pytest.fixture
async def seeded_questionnaire(db_session: AsyncSession) -> Questionnaire:
    """Instrumento padrão de 10 soft skills, aplicado pelo seed da aplicação."""
    return await seed_default_questionnaire(db_session)


def client_for(base: AsyncClient, token: str) -> AsyncClient:
    """Novo client HTTP reutilizando o transporte de teste, com outro usuário."""
    return AsyncClient(
        transport=base._transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    )


def choose_options(questions, trait_preference: dict[str, float], spread: float = 0.35) -> list[dict[str, str]]:
    """Simula uma pessoa respondendo o SJT com uma tendência de traço estável.

    Em cada cenário escolhe a conduta que melhor casa com a preferência dada —
    é assim que os testes descrevem um respondente ("alguém que privilegia
    Amabilidade e Estabilidade") sem enumerar as 20 escolhas à mão.

    `spread` rotaciona um pequeno favorecimento entre os fatores ao longo dos
    itens. Sem isso o respondente simulado escolheria o mesmo traço nas 20
    situações — uma consistência que nenhuma pessoa real tem, e que produziria
    perfis artificialmente extremos.

    Traços ausentes de `trait_preference` valem 0: a pessoa não os evita, apenas
    não os prioriza quando há alternativa mais alinhada.
    """
    payload = []
    for index, question in enumerate(questions):
        boosted = TRAITS[index % len(TRAITS)]

        def affinity(option, boosted=boosted):
            return sum(
                (trait_preference.get(trait, 0.0) + (spread if trait == boosted else 0.0)) * weight
                for trait, weight in option.loadings_map().items()
            )

        best = max(question.options, key=affinity)
        payload.append({"question_id": str(question.id), "selected_option_id": str(best.id)})
    return payload


async def join_team_and_answer(
    base_client: AsyncClient,
    invite_token: str,
    suffix: str,
    questionnaire,
    trait_preference: dict[str, float],
) -> str:
    """Convida alguém para o time e responde o diagnóstico com esse perfil.

    O responsável pelo time **não** é integrante, então todo respondente do
    diagnóstico entra por convite — inclusive nos testes.
    """
    auth = await base_client.post(
        "/api/v1/auth/google",
        json={"id_token": f"mock_google_token_{suffix}", "invite_token": invite_token},
    )
    assert auth.status_code == 200, auth.text

    member = client_for(base_client, auth.json()["access_token"])
    await answer_questionnaire(member, questionnaire.id, questionnaire.questions, trait_preference)
    return auth.json()["user"]["id"]


async def answer_questionnaire(
    client: AsyncClient,
    questionnaire_id,
    questions,
    trait_preference: dict[str, float],
    spread: float = 0.35,
) -> None:
    """Responde o instrumento inteiro com uma tendência de traço consistente."""
    response = await client.post(
        f"/api/v1/questionnaires/{questionnaire_id}/answers",
        json={"answers": choose_options(questions, trait_preference, spread)},
    )
    assert response.status_code == 200, response.text
