import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.questionnaire import Question, Questionnaire


@pytest.fixture
async def setup_questionnaire(db_session: AsyncSession) -> Questionnaire:
    q = Questionnaire(
        title="Default Soft Skills Questionnaire",
        description="Standard assessment",
    )
    db_session.add(q)
    await db_session.commit()
    await db_session.refresh(q)

    dimensions = [
        "Comunicação",
        "Liderança",
        "Adaptabilidade",
        "Trabalho em Equipe",
    ]
    for dim in dimensions:
        q_item = Question(
            questionnaire_id=q.id,
            dimension=dim,
            text=f"Avalie sua habilidade em {dim}",
        )
        db_session.add(q_item)

    await db_session.commit()
    await db_session.refresh(q)
    return q


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
    response = await authenticated_client.get(
        f"/api/v1/jobs/{random_job_id}/candidates"
    )

    # Assert
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_job_candidates_validation_error(authenticated_client: AsyncClient):
    # Arrange
    invalid_job_id = "invalid-uuid"

    # Act
    response = await authenticated_client.get(
        f"/api/v1/jobs/{invalid_job_id}/candidates"
    )

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


@pytest.mark.asyncio
async def test_full_impact_analysis_flow(
    authenticated_client: AsyncClient,
    setup_questionnaire: Questionnaire,
    db_session: AsyncSession,
):
    # 1. Create a Team
    team_resp = await authenticated_client.post(
        "/api/v1/teams", json={"name": "DevOps Team"}
    )
    assert team_resp.status_code == 201
    team_id = team_resp.json()["id"]

    # 2. Create a Job linked to Team and Questionnaire
    job_payload = {
        "title": "Senior DevOps Engineer",
        "description": "Lead cloud infra",
        "team_id": team_id,
        "questionnaire_id": str(setup_questionnaire.id),
    }
    job_resp = await authenticated_client.post(
        "/api/v1/jobs", json=job_payload
    )
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]

    # 3. Authenticate Candidate 1 (Completed Answers) & Candidate 2 (No Answers)
    cand1_auth = await authenticated_client.post(
        "/api/v1/auth/google",
        json={"id_token": "mock_google_token_cand1", "job_id": job_id},
    )
    assert cand1_auth.status_code == 200
    cand1_token = cand1_auth.json()["access_token"]
    candidate1_id = cand1_auth.json()["user"]["id"]

    cand2_auth = await authenticated_client.post(
        "/api/v1/auth/google",
        json={"id_token": "mock_google_token_cand2", "job_id": job_id},
    )
    assert cand2_auth.status_code == 200
    candidate2_id = cand2_auth.json()["user"]["id"]

    # 4. Candidate 1 submits answers to questionnaire
    stmt = select(Question).where(
        Question.questionnaire_id == setup_questionnaire.id
    )
    res = await db_session.execute(stmt)
    questions = list(res.scalars().all())

    answers_payload = {
        "answers": [
            {"question_id": str(questions[0].id), "score": 5},
            {"question_id": str(questions[1].id), "score": 4},
            {"question_id": str(questions[2].id), "score": 4},
            {"question_id": str(questions[3].id), "score": 5},
        ]
    }
    cand_client = AsyncClient(
        transport=authenticated_client._transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {cand1_token}"},
    )
    ans_resp = await cand_client.post(
        f"/api/v1/jobs/{job_id}/answers", json=answers_payload
    )
    assert ans_resp.status_code == 200

    # 5. Recruiter fetches candidates list for the job
    candidates_resp = await authenticated_client.get(
        f"/api/v1/jobs/{job_id}/candidates"
    )
    assert candidates_resp.status_code == 200
    cand_list = candidates_resp.json()
    assert len(cand_list) == 2

    # 6. Test query params filtering by min_fit_score and limit
    # Filter with min_fit_score=50.0 -> Only Candidate 1 (with completed fit_score) returned
    filter_pass = await authenticated_client.get(
        f"/api/v1/jobs/{job_id}/candidates?min_fit_score=50.0&limit=10"
    )
    assert filter_pass.status_code == 200
    assert len(filter_pass.json()) == 1
    assert filter_pass.json()[0]["candidate_id"] == candidate1_id

    # Filter with status=APPLIED -> Candidate 2 returned
    filter_status = await authenticated_client.get(
        f"/api/v1/jobs/{job_id}/candidates?status=APPLIED"
    )
    assert filter_status.status_code == 200
    assert len(filter_status.json()) == 1
    assert filter_status.json()[0]["candidate_id"] == candidate2_id

    # Filter with limit=1 -> Top 1 candidate returned
    filter_limit = await authenticated_client.get(
        f"/api/v1/jobs/{job_id}/candidates?limit=1"
    )
    assert filter_limit.status_code == 200
    assert len(filter_limit.json()) == 1

    # 7. Recruiter runs Impact Analysis & Post-Hiring Simulation
    impact_resp = await authenticated_client.post(
        f"/api/v1/jobs/{job_id}/candidates/{candidate1_id}/impact-analysis"
    )
    assert impact_resp.status_code == 200
    impact_data = impact_resp.json()

    assert impact_data["job_id"] == job_id
    assert impact_data["candidate_id"] == candidate1_id
    assert "candidate_scores" in impact_data
    assert "current_team_scores" in impact_data
    assert "simulation" in impact_data

    sim = impact_data["simulation"]
    assert sim["new_team_size"] == sim["current_team_size"] + 1
    assert "simulated_team_scores" in sim
    assert "score_deltas" in sim
