import pytest
from httpx import AsyncClient


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


@pytest.mark.asyncio
async def test_get_me_unauthorized(async_client: AsyncClient):
    # Arrange: client without Authorization header

    # Act
    response = await async_client.get("/api/v1/auth/me")

    # Assert
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
