import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_team_success(authenticated_client: AsyncClient):
    # Arrange
    payload = {"name": "Engineering Team"}

    # Act
    response = await authenticated_client.post("/api/v1/teams", json=payload)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Engineering Team"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_team_validation_error(authenticated_client: AsyncClient):
    # Arrange: payload missing required name
    payload = {}

    # Act
    response = await authenticated_client.post("/api/v1/teams", json=payload)

    # Assert
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_team_unauthorized(async_client: AsyncClient):
    # Arrange
    payload = {"name": "Engineering Team"}

    # Act
    response = await async_client.post("/api/v1/teams", json=payload)

    # Assert
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_team_profile_success(authenticated_client: AsyncClient):
    # Arrange: create team first
    team_resp = await authenticated_client.post(
        "/api/v1/teams", json={"name": "Product Team"}
    )
    team_id = team_resp.json()["id"]

    # Act
    response = await authenticated_client.get(
        f"/api/v1/teams/{team_id}/soft-skills-profile"
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["team_id"] == team_id
    assert data["team_name"] == "Product Team"
    assert "dimension_scores" in data


@pytest.mark.asyncio
async def test_get_team_profile_not_found(authenticated_client: AsyncClient):
    # Arrange: random non-existent UUID
    random_id = str(uuid.uuid4())

    # Act
    response = await authenticated_client.get(
        f"/api/v1/teams/{random_id}/soft-skills-profile"
    )

    # Assert
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_team_profile_validation_error(authenticated_client: AsyncClient):
    # Arrange: invalid UUID string
    invalid_id = "not-a-valid-uuid"

    # Act
    response = await authenticated_client.get(
        f"/api/v1/teams/{invalid_id}/soft-skills-profile"
    )

    # Assert
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_team_profile_unauthorized(async_client: AsyncClient):
    # Arrange
    random_id = str(uuid.uuid4())

    # Act
    response = await async_client.get(f"/api/v1/teams/{random_id}/soft-skills-profile")

    # Assert
    assert response.status_code == 401
