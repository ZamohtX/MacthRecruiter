import uuid

import pytest
from httpx import AsyncClient

from app.core.big_five import SJT_SCENARIOS, Trait
from app.core.soft_skills import DIMENSIONS, Dimension
from app.models.questionnaire import Questionnaire
from tests.conftest import choose_options, client_for, join_team_and_answer

# Perfil do time: exploradores. Privilegiam Abertura, quase nunca escolhem a
# conduta cooperativa — vira força em Criatividade e lacuna em Colaboração.
EXPLORER = {
    Trait.ABERTURA: 1.4,
    Trait.CONSCIENCIOSIDADE: 0.5,
    Trait.EXTROVERSAO: 0.2,
    Trait.AMABILIDADE: 0.1,
    Trait.ESTABILIDADE: 0.2,
}

# Candidato que cobre a lacuna: privilegia as condutas cooperativas e de
# regulação emocional que o time evita.
CONNECTOR = {
    Trait.AMABILIDADE: 1.4,
    Trait.EXTROVERSAO: 1.0,
    Trait.ESTABILIDADE: 0.8,
    Trait.CONSCIENCIOSIDADE: 0.4,
    Trait.ABERTURA: 0.1,
}


@pytest.mark.asyncio
async def test_job_candidates_unauthorized(async_client: AsyncClient):
    # Arrange
    random_job_id = str(uuid.uuid4())

    # Act
    response = await async_client.get(f"/api/v1/jobs/{random_job_id}/candidates")

    # Assert
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_job_candidates_not_found(authenticated_client: AsyncClient):
    # Arrange
    random_job_id = str(uuid.uuid4())

    # Act
    response = await authenticated_client.get(f"/api/v1/jobs/{random_job_id}/candidates")

    # Assert
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_job_candidates_validation_error(authenticated_client: AsyncClient):
    # Arrange
    invalid_job_id = "invalid-uuid"

    # Act
    response = await authenticated_client.get(f"/api/v1/jobs/{invalid_job_id}/candidates")

    # Assert
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_impact_analysis_not_found(authenticated_client: AsyncClient):
    # Arrange
    random_job_id = str(uuid.uuid4())
    random_cand_id = str(uuid.uuid4())

    # Act
    response = await authenticated_client.post(
        f"/api/v1/jobs/{random_job_id}/candidates/{random_cand_id}/impact-analysis"
    )

    # Assert
    assert response.status_code == 404


@pytest.fixture
async def diagnosed_team(authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire) -> dict:
    """Time de 4 exploradores já diagnosticado, com a vaga aberta.

    Força consolidada em Criatividade; lacuna funda em Colaboração — o cenário
    que o produto existe para tratar.

    O recrutador que cria o time é apenas responsável: todos os quatro
    respondentes entram por convite.
    """
    team_resp = await authenticated_client.post("/api/v1/teams", json={"name": "Squad Explorador"})
    team_id = team_resp.json()["id"]

    invite_resp = await authenticated_client.post(f"/api/v1/teams/{team_id}/invites")
    invite_token = invite_resp.json()["invite_token"]

    for suffix in ("m1", "m2", "m3", "m4"):
        await join_team_and_answer(authenticated_client, invite_token, suffix, seeded_questionnaire, EXPLORER)

    job_resp = await authenticated_client.post("/api/v1/jobs", json={"title": "Dev Backend Pleno", "team_id": team_id})
    assert job_resp.status_code == 201, job_resp.text

    return {"team_id": team_id, "job_id": job_resp.json()["id"], "questionnaire": seeded_questionnaire}


async def _apply_and_answer(
    base_client: AsyncClient, job_id: str, token_suffix: str, questions, trait_preference: dict
) -> str:
    """Candidata-se à vaga e responde o SJT com a tendência de traço informada."""
    auth = await base_client.post(
        "/api/v1/auth/google", json={"id_token": f"mock_google_token_{token_suffix}", "job_id": job_id}
    )
    assert auth.status_code == 200
    candidate_id = auth.json()["user"]["id"]

    candidate_client = client_for(base_client, auth.json()["access_token"])
    response = await candidate_client.post(
        f"/api/v1/jobs/{job_id}/answers", json={"answers": choose_options(questions, trait_preference)}
    )
    assert response.status_code == 200, response.text
    return candidate_id


@pytest.mark.asyncio
async def test_create_job_defaults_to_standard_questionnaire(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    # Arrange
    team_resp = await authenticated_client.post("/api/v1/teams", json={"name": "Time Padrão"})

    # Act
    response = await authenticated_client.post("/api/v1/jobs", json={"title": "Dev", "team_id": team_resp.json()["id"]})

    # Assert
    assert response.status_code == 201
    assert response.json()["questionnaire_id"] == str(seeded_questionnaire.id)


@pytest.mark.asyncio
async def test_create_job_forbidden_for_team_of_another_recruiter(
    authenticated_client: AsyncClient, other_recruiter_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    # Arrange
    team_resp = await authenticated_client.post("/api/v1/teams", json={"name": "Time Privado"})

    # Act
    response = await other_recruiter_client.post(
        "/api/v1/jobs", json={"title": "Vaga Intrusa", "team_id": team_resp.json()["id"]}
    )

    # Assert
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_job_with_unknown_team_returns_404(authenticated_client: AsyncClient):
    # Act
    response = await authenticated_client.post("/api/v1/jobs", json={"title": "Dev", "team_id": str(uuid.uuid4())})

    # Assert
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_candidate_list_forbidden_for_outsider(
    authenticated_client: AsyncClient, other_recruiter_client: AsyncClient, diagnosed_team: dict
):
    """Perfil comportamental de candidato não pode vazar entre empresas."""
    # Act
    response = await other_recruiter_client.get(f"/api/v1/jobs/{diagnosed_team['job_id']}/candidates")

    # Assert
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_job_questionnaire_matches_the_one_team_answered(authenticated_client: AsyncClient, diagnosed_team: dict):
    # Act
    response = await authenticated_client.get(f"/api/v1/jobs/{diagnosed_team['job_id']}/questionnaire")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(diagnosed_team["questionnaire"].id)
    assert data["format"] == "SJT"
    assert len(data["questions"]) == len(SJT_SCENARIOS)


@pytest.mark.asyncio
async def test_partial_answers_do_not_complete_the_application(authenticated_client: AsyncClient, diagnosed_team: dict):
    # Arrange
    job_id = diagnosed_team["job_id"]
    questions = diagnosed_team["questionnaire"].questions
    auth = await authenticated_client.post(
        "/api/v1/auth/google", json={"id_token": "mock_google_token_partial", "job_id": job_id}
    )
    candidate_client = client_for(authenticated_client, auth.json()["access_token"])

    # Act: responde só metade dos cenários
    response = await candidate_client.post(
        f"/api/v1/jobs/{job_id}/answers", json={"answers": choose_options(questions[:10], CONNECTOR)}
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["progress"]["is_complete"] is False

    candidates = await authenticated_client.get(f"/api/v1/jobs/{job_id}/candidates")
    entry = next(c for c in candidates.json() if c["candidate_id"] == auth.json()["user"]["id"])
    assert entry["status"] == "APPLIED"


@pytest.mark.asyncio
async def test_complementary_candidate_outranks_the_team_mirror(
    authenticated_client: AsyncClient, diagnosed_team: dict
):
    """O teste que prova a tese do produto ponta a ponta.

    O candidato-espelho responde o SJT exatamente como o time. Um ATS comum o
    veria como "encaixe cultural perfeito"; aqui ele é o pior colocado.
    """
    # Arrange
    job_id = diagnosed_team["job_id"]
    questions = diagnosed_team["questionnaire"].questions

    complementary_id = await _apply_and_answer(authenticated_client, job_id, "conector", questions, CONNECTOR)
    mirror_id = await _apply_and_answer(authenticated_client, job_id, "espelho", questions, EXPLORER)

    # Act
    response = await authenticated_client.get(f"/api/v1/jobs/{job_id}/candidates")

    # Assert
    assert response.status_code == 200
    ranking = response.json()
    assert [c["candidate_id"] for c in ranking] == [complementary_id, mirror_id]
    assert ranking[0]["fit_score"] > ranking[1]["fit_score"]

    # O espelho é idêntico ao time — fit suplementar máximo, complementar mínimo
    assert ranking[1]["supplementary_fit_index"] == 100.0
    assert ranking[0]["supplementary_fit_index"] < ranking[1]["supplementary_fit_index"]
    assert ranking[1]["gaps_filled"] == []

    # O complementar cobre a competência que o time não tem
    assert Dimension.COLABORACAO in ranking[0]["gaps_filled"]


@pytest.mark.asyncio
async def test_impact_analysis_explains_every_dimension(authenticated_client: AsyncClient, diagnosed_team: dict):
    # Arrange
    job_id = diagnosed_team["job_id"]
    candidate_id = await _apply_and_answer(
        authenticated_client, job_id, "explica", diagnosed_team["questionnaire"].questions, CONNECTOR
    )

    # Act
    response = await authenticated_client.post(f"/api/v1/jobs/{job_id}/candidates/{candidate_id}/impact-analysis")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["simulation"]["current_team_size"] == 4
    assert data["simulation"]["new_team_size"] == 5
    assert data["simulation"]["score_deltas"][Dimension.COLABORACAO] > 0
    assert Dimension.COLABORACAO in data["simulation"]["gaps_filled"]
    assert len(data["insights"]) == len(DIMENSIONS)
    assert all(i["explanation"] for i in data["insights"])
    assert data["complementary_fit_score"] == data["fit_score"]


@pytest.mark.asyncio
async def test_mirror_candidate_shows_the_cost_of_hiring_more_of_the_same(
    authenticated_client: AsyncClient, diagnosed_team: dict
):
    """A simulação precisa mostrar que o espelho não move nada."""
    # Arrange
    job_id = diagnosed_team["job_id"]
    candidate_id = await _apply_and_answer(
        authenticated_client, job_id, "clone", diagnosed_team["questionnaire"].questions, EXPLORER
    )

    # Act
    response = await authenticated_client.post(f"/api/v1/jobs/{job_id}/candidates/{candidate_id}/impact-analysis")

    # Assert
    data = response.json()
    assert data["supplementary_fit_index"] == 100.0
    assert data["gap_coverage"] == 0.0
    # Contratar um clone não altera média nenhuma
    assert all(delta == 0.0 for delta in data["simulation"]["score_deltas"].values())
    assert Dimension.COLABORACAO in data["simulation"]["gaps_missed"]
    assert data["risk_flags"]


@pytest.mark.asyncio
async def test_update_candidate_status(authenticated_client: AsyncClient, diagnosed_team: dict):
    # Arrange
    job_id = diagnosed_team["job_id"]
    candidate_id = await _apply_and_answer(
        authenticated_client, job_id, "status", diagnosed_team["questionnaire"].questions, CONNECTOR
    )

    # Act
    response = await authenticated_client.patch(
        f"/api/v1/jobs/{job_id}/candidates/{candidate_id}/status", json={"status": "UNDER_REVIEW"}
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "UNDER_REVIEW"


@pytest.mark.asyncio
async def test_update_candidate_status_validation_error(authenticated_client: AsyncClient, diagnosed_team: dict):
    # Act
    response = await authenticated_client.patch(
        f"/api/v1/jobs/{diagnosed_team['job_id']}/candidates/{uuid.uuid4()}/status",
        json={"status": "NAO_EXISTE"},
    )

    # Assert
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_candidate_status_not_found(authenticated_client: AsyncClient, diagnosed_team: dict):
    # Act
    response = await authenticated_client.patch(
        f"/api/v1/jobs/{diagnosed_team['job_id']}/candidates/{uuid.uuid4()}/status",
        json={"status": "REJECTED"},
    )

    # Assert
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_hiring_adds_candidate_to_the_team_and_shifts_its_profile(
    authenticated_client: AsyncClient, diagnosed_team: dict
):
    """Fecha o ciclo: a simulação vira o diagnóstico real do time."""
    # Arrange
    job_id, team_id = diagnosed_team["job_id"], diagnosed_team["team_id"]
    candidate_id = await _apply_and_answer(
        authenticated_client, job_id, "contratado", diagnosed_team["questionnaire"].questions, CONNECTOR
    )

    before = await authenticated_client.get(f"/api/v1/teams/{team_id}/soft-skills-profile")
    simulated = await authenticated_client.post(f"/api/v1/jobs/{job_id}/candidates/{candidate_id}/impact-analysis")
    predicted = simulated.json()["simulation"]["simulated_team_scores"]

    # Act
    hire = await authenticated_client.post(f"/api/v1/jobs/{job_id}/candidates/{candidate_id}/hire")

    # Assert
    assert hire.status_code == 200
    assert hire.json()["status"] == "HIRED"

    after = await authenticated_client.get(f"/api/v1/teams/{team_id}/soft-skills-profile")
    assert after.json()["member_count"] == before.json()["member_count"] + 1
    assert after.json()["dimension_scores"][Dimension.COLABORACAO] == pytest.approx(
        predicted[Dimension.COLABORACAO], abs=0.05
    )


@pytest.mark.asyncio
async def test_list_my_jobs(authenticated_client: AsyncClient, diagnosed_team: dict):
    # Act
    response = await authenticated_client.get("/api/v1/jobs")

    # Assert
    assert response.status_code == 200
    assert [j["id"] for j in response.json()] == [diagnosed_team["job_id"]]


@pytest.mark.asyncio
async def test_get_job_detail(authenticated_client: AsyncClient, diagnosed_team: dict):
    # Act
    response = await authenticated_client.get(f"/api/v1/jobs/{diagnosed_team['job_id']}")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["team_name"] == "Squad Explorador"
    assert data["team_assessment_ready"] is True
