import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.core.config import DEV_SECRET_KEY, MOCK_GOOGLE_CLIENT_ID, Settings, settings
from app.core.security import _mock_login_allowed


@pytest.mark.asyncio
async def test_login_google_success_recruiter(async_client: AsyncClient):
    # Arrange
    payload = {
        "id_token": "mock_google_token_recruiter",
        "invite_token": None,
        "job_id": None,
    }

    # Act
    response = await async_client.post("/api/v1/auth/google", json=payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "RECRUITER"
    assert data["user"]["email"] == "user_recruiter@example.com"


@pytest.mark.asyncio
async def test_login_google_validation_error(async_client: AsyncClient):
    # Arrange: payload missing required id_token
    payload = {}

    # Act
    response = await async_client.post("/api/v1/auth/google", json=payload)

    # Assert
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_mock_login_available_in_development():
    assert _mock_login_allowed("mock_google_token_recruiter") is True


def test_mock_login_rejected_in_production(monkeypatch: pytest.MonkeyPatch):
    """Um token forjado com o prefixo do mock não pode virar sessão válida.

    Este era o buraco: o prefixo sozinho liberava o login mesmo com um
    GOOGLE_CLIENT_ID real configurado.
    """
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    assert _mock_login_allowed("mock_google_token_admin") is False


def test_production_rejects_development_defaults():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            SECRET_KEY=DEV_SECRET_KEY,
            GOOGLE_CLIENT_ID=MOCK_GOOGLE_CLIENT_ID,
            CORS_ORIGINS=["*"],
            DATABASE_URL="postgresql+asyncpg://user:pass@host/db",
        )

    message = str(exc_info.value)
    assert "SECRET_KEY" in message
    assert "GOOGLE_CLIENT_ID" in message
    assert "CORS_ORIGINS" in message


def test_production_accepts_real_configuration():
    config = Settings(
        _env_file=None,
        ENVIRONMENT="production",
        SECRET_KEY="a" * 48,
        GOOGLE_CLIENT_ID="real-client.apps.googleusercontent.com",
        CORS_ORIGINS=["https://matchrecruiter.web.app"],
        DATABASE_URL="postgresql+asyncpg://user:pass@/matchrecruiter?host=/cloudsql/p:r:i",
    )

    assert config.is_production is True


@pytest.mark.asyncio
async def test_get_me_unauthorized(async_client: AsyncClient):
    # Arrange: client without Authorization header

    # Act
    response = await async_client.get("/api/v1/auth/me")

    # Assert
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
