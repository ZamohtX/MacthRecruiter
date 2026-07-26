import uuid

import pytest
from httpx import AsyncClient

from app.core.big_five import SJT_SCENARIOS, TRAITS, Trait
from app.core.soft_skills import MIN_CANDIDATE_FLOOR, Dimension
from app.models.questionnaire import Questionnaire
from tests.conftest import answer_questionnaire, join_team_and_answer


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
    team_resp = await authenticated_client.post("/api/v1/teams", json={"name": "Product Team"})
    team_id = team_resp.json()["id"]

    # Act
    response = await authenticated_client.get(f"/api/v1/teams/{team_id}/soft-skills-profile")

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
    response = await authenticated_client.get(f"/api/v1/teams/{random_id}/soft-skills-profile")

    # Assert
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_team_profile_validation_error(authenticated_client: AsyncClient):
    # Arrange: invalid UUID string
    invalid_id = "not-a-valid-uuid"

    # Act
    response = await authenticated_client.get(f"/api/v1/teams/{invalid_id}/soft-skills-profile")

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


@pytest.mark.asyncio
async def test_list_my_teams_returns_only_own_teams(
    authenticated_client: AsyncClient, other_recruiter_client: AsyncClient
):
    # Arrange
    await authenticated_client.post("/api/v1/teams", json={"name": "Meu Time"})
    await other_recruiter_client.post("/api/v1/teams", json={"name": "Time Alheio"})

    # Act
    response = await authenticated_client.get("/api/v1/teams")

    # Assert
    assert response.status_code == 200
    names = [t["name"] for t in response.json()]
    assert names == ["Meu Time"]


@pytest.mark.asyncio
async def test_team_profile_forbidden_for_outsider(
    authenticated_client: AsyncClient, other_recruiter_client: AsyncClient
):
    # Arrange
    team_resp = await authenticated_client.post("/api/v1/teams", json={"name": "Time Privado"})
    team_id = team_resp.json()["id"]

    # Act
    response = await other_recruiter_client.get(f"/api/v1/teams/{team_id}/soft-skills-profile")

    # Assert
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_team_profile_flags_low_confidence_without_respondents(authenticated_client: AsyncClient):
    # Arrange
    team_resp = await authenticated_client.post("/api/v1/teams", json={"name": "Time Novo"})
    team_id = team_resp.json()["id"]

    # Act
    response = await authenticated_client.get(f"/api/v1/teams/{team_id}/soft-skills-profile")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["respondent_count"] == 0
    assert data["low_confidence"] is True
    assert "Nenhum integrante" in data["confidence_note"]


@pytest.mark.asyncio
async def test_diagnostic_status_tracks_who_answered(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    # Arrange
    team_resp = await authenticated_client.post("/api/v1/teams", json={"name": "Squad Backend"})
    team_id = team_resp.json()["id"]

    invite = await authenticated_client.post(f"/api/v1/teams/{team_id}/invites")
    invite_token = invite.json()["invite_token"]

    # Act: time recém-criado, sem ninguém dentro — o responsável não é integrante
    before = await authenticated_client.get(f"/api/v1/teams/{team_id}/diagnostic-status")

    # Assert
    assert before.status_code == 200
    assert before.json()["member_count"] == 0
    assert before.json()["respondent_count"] == 0
    assert before.json()["ready_for_job_opening"] is False
    assert before.json()["members"] == []

    # Act: um integrante entra pelo convite e responde
    await join_team_and_answer(
        authenticated_client, invite_token, "diag1", seeded_questionnaire, {Trait.CONSCIENCIOSIDADE: 1.0}
    )
    after = await authenticated_client.get(f"/api/v1/teams/{team_id}/diagnostic-status")

    # Assert
    data = after.json()
    assert data["member_count"] == 1
    assert data["respondent_count"] == 1
    assert data["members"][0]["assessment_completed"] is True
    assert data["members"][0]["answered_questions"] == len(SJT_SCENARIOS)
    assert data["members"][0]["is_owner"] is False


@pytest.mark.asyncio
async def test_gap_analysis_prioritizes_weakest_dimensions(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    # Arrange: time de exploradores — privilegia Abertura, quase nunca escolhe
    # a conduta cooperativa. Vira força em Criatividade e lacuna em Colaboração.
    team_resp = await authenticated_client.post("/api/v1/teams", json={"name": "Squad Explorador"})
    team_id = team_resp.json()["id"]
    invite = await authenticated_client.post(f"/api/v1/teams/{team_id}/invites")

    await join_team_and_answer(
        authenticated_client,
        invite.json()["invite_token"],
        "explorador1",
        seeded_questionnaire,
        {
            Trait.ABERTURA: 1.4,
            Trait.CONSCIENCIOSIDADE: 0.5,
            Trait.EXTROVERSAO: 0.2,
            Trait.AMABILIDADE: 0.1,
            Trait.ESTABILIDADE: 0.2,
        },
    )

    # Act
    response = await authenticated_client.get(f"/api/v1/teams/{team_id}/gap-analysis")

    # Assert
    assert response.status_code == 200
    data = response.json()

    # A lacuna mais funda é a competência que o time nunca privilegiou
    assert data["priority_dimensions"][0] == Dimension.COLABORACAO
    assert Dimension.CRIATIVIDADE in data["strengths"]

    weights = {d["dimension"]: d["weight"] for d in data["dimensions"]}
    assert weights[Dimension.COLABORACAO] > weights[Dimension.COMUNICACAO]
    assert weights[Dimension.CRIATIVIDADE] == 0.0

    # O alvo da lacuna é o ponto em que ela deixaria de ser lacuna neste time —
    # relativo ao perfil, não um número fixo. Nas demais vale o piso mínimo.
    scores = {d["dimension"]: d["team_score"] for d in data["dimensions"]}
    center = sum(scores.values()) / len(scores)
    assert data["target_profile"][Dimension.COLABORACAO] > center
    assert data["target_profile"][Dimension.CRIATIVIDADE] == MIN_CANDIDATE_FLOOR

    # Cada peso vem com justificativa rastreável
    colaboracao = next(d for d in data["dimensions"] if d["dimension"] == Dimension.COLABORACAO)
    assert "abaixo do nível médio do próprio time" in colaboracao["rationale"]


@pytest.mark.asyncio
async def test_team_profile_exposes_both_latent_traits_and_derived_skills(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    """O gestor precisa das duas camadas: os fatores dizem que tipo de gente é o
    time; as competências são o que entra na lacuna e no fit."""
    # Arrange
    team_resp = await authenticated_client.post("/api/v1/teams", json={"name": "Squad Organizado"})
    team_id = team_resp.json()["id"]
    invite = await authenticated_client.post(f"/api/v1/teams/{team_id}/invites")

    await join_team_and_answer(
        authenticated_client,
        invite.json()["invite_token"],
        "organizado1",
        seeded_questionnaire,
        {Trait.CONSCIENCIOSIDADE: 1.4, Trait.ABERTURA: 0.5, Trait.ESTABILIDADE: 0.4},
    )

    # Act
    response = await authenticated_client.get(f"/api/v1/teams/{team_id}/soft-skills-profile")

    # Assert
    data = response.json()
    assert set(data["trait_scores"]) == set(TRAITS)
    assert data["trait_scores"][Trait.CONSCIENCIOSIDADE] > 4.0
    assert data["dimension_scores"][Dimension.DISCIPLINA] > 4.0


async def test_gap_analysis_forbidden_for_outsider(
    authenticated_client: AsyncClient, other_recruiter_client: AsyncClient
):
    # Arrange
    team_resp = await authenticated_client.post("/api/v1/teams", json={"name": "Time Privado"})
    team_id = team_resp.json()["id"]

    # Act
    response = await other_recruiter_client.get(f"/api/v1/teams/{team_id}/gap-analysis")

    # Assert
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_gap_analysis_not_found(authenticated_client: AsyncClient):
    # Act
    response = await authenticated_client.get(f"/api/v1/teams/{uuid.uuid4()}/gap-analysis")

    # Assert
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_invite_token_carries_expiry(authenticated_client: AsyncClient):
    # Arrange
    team_resp = await authenticated_client.post("/api/v1/teams", json={"name": "Time Convite"})
    team_id = team_resp.json()["id"]

    # Act
    response = await authenticated_client.post(f"/api/v1/teams/{team_id}/invites")

    # Assert
    assert response.status_code == 201
    assert response.json()["expires_at"] is not None


@pytest.mark.asyncio
async def test_team_creator_is_responsible_but_not_a_member(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    """O recrutador administra o time sem entrar no diagnóstico.

    Incluí-lo contaminaria a média com o perfil de quem não convive com o
    problema que a vaga vai resolver — e o obrigaria a responder o teste.
    """
    # Arrange
    team_resp = await authenticated_client.post("/api/v1/teams", json={"name": "Squad do RH"})
    team_id = team_resp.json()["id"]

    # Act: o responsável responde o instrumento por conta própria
    await answer_questionnaire(
        authenticated_client,
        seeded_questionnaire.id,
        seeded_questionnaire.questions,
        {Trait.CONSCIENCIOSIDADE: 1.4},
    )
    profile = await authenticated_client.get(f"/api/v1/teams/{team_id}/soft-skills-profile")

    # Assert: as respostas dele não entram no perfil do time
    data = profile.json()
    assert data["member_count"] == 0
    assert data["respondent_count"] == 0
    assert data["dimension_scores"] == {}

    # …mas ele continua administrando o time
    assert (await authenticated_client.post(f"/api/v1/teams/{team_id}/invites")).status_code == 201
    assert (await authenticated_client.get(f"/api/v1/teams/{team_id}/gap-analysis")).status_code == 200
