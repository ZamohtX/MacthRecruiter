import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.big_five import SJT_SCENARIOS, TRAITS, Trait
from app.core.soft_skills import DIMENSIONS
from app.db.seed import seed_default_questionnaire
from app.models.questionnaire import Questionnaire
from tests.conftest import choose_options


@pytest.mark.asyncio
async def test_get_default_questionnaire_returns_sjt_scenarios_with_options(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    # Act
    response = await authenticated_client.get("/api/v1/questionnaires/default")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["is_default"] is True
    assert data["format"] == "SJT"
    assert data["traits"] == list(TRAITS)
    assert data["derived_dimensions"] == list(DIMENSIONS)
    assert len(data["questions"]) == len(SJT_SCENARIOS)

    scenario = data["questions"][0]
    assert scenario["context"]
    assert len(scenario["options"]) >= 3
    assert all(o["text"] for o in scenario["options"])


@pytest.mark.asyncio
async def test_options_never_expose_their_trait_loadings(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    """Se o respondente vir que uma alternativa pontua Conscienciosidade, ele
    escolhe pelo rótulo — é a desejabilidade social que o SJT existe para evitar.

    O cabeçalho pode declarar *quais* fatores o instrumento mede (transparência
    que a LGPD favorece); o que não pode vazar é o mapa alternativa → fator.
    """
    # Act
    response = await authenticated_client.get("/api/v1/questionnaires/default")

    # Assert
    import json

    questions_payload = json.dumps(response.json()["questions"], ensure_ascii=False)
    for trait in TRAITS:
        assert trait not in questions_payload
    assert "loading" not in questions_payload.lower()

    for question in response.json()["questions"]:
        for option in question["options"]:
            assert set(option) == {"id", "text", "position"}


@pytest.mark.asyncio
async def test_get_default_questionnaire_not_found_without_seed(authenticated_client: AsyncClient):
    # Arrange: banco sem seed aplicado

    # Act
    response = await authenticated_client.get("/api/v1/questionnaires/default")

    # Assert
    assert response.status_code == 404
    assert "seed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_questionnaires_unauthorized(async_client: AsyncClient):
    # Act
    response = await async_client.get("/api/v1/questionnaires")

    # Assert
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_questionnaire_not_found(authenticated_client: AsyncClient):
    # Act
    response = await authenticated_client.get(f"/api/v1/questionnaires/{uuid.uuid4()}")

    # Assert
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_questionnaire_validation_error(authenticated_client: AsyncClient):
    # Act
    response = await authenticated_client.get("/api/v1/questionnaires/not-a-uuid")

    # Assert
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_answers_reports_partial_progress(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    # Arrange: responde apenas 3 dos 20 cenários
    payload = {"answers": choose_options(seeded_questionnaire.questions[:3], {Trait.CONSCIENCIOSIDADE: 1.0})}

    # Act
    response = await authenticated_client.post(
        f"/api/v1/questionnaires/{seeded_questionnaire.id}/answers", json=payload
    )

    # Assert
    assert response.status_code == 200
    progress = response.json()["progress"]
    assert progress["answered_questions"] == 3
    assert progress["total_questions"] == len(SJT_SCENARIOS)
    assert progress["is_complete"] is False
    assert len(progress["missing_question_ids"]) == len(SJT_SCENARIOS) - 3


@pytest.mark.asyncio
async def test_completing_the_test_yields_both_traits_and_derived_skills(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    # Arrange: alguém que privilegia consistentemente Conscienciosidade
    payload = {"answers": choose_options(seeded_questionnaire.questions, {Trait.CONSCIENCIOSIDADE: 1.0})}

    # Act
    response = await authenticated_client.post(
        f"/api/v1/questionnaires/{seeded_questionnaire.id}/answers", json=payload
    )

    # Assert
    assert response.status_code == 200
    progress = response.json()["progress"]
    assert progress["is_complete"] is True

    # Camada latente medida
    assert set(progress["trait_scores"]) == set(TRAITS)
    assert progress["trait_scores"][Trait.CONSCIENCIOSIDADE] == 5.0

    # Camada observável derivada — Disciplina carrega 0.80 em Conscienciosidade
    assert set(progress["dimension_scores"]) == set(DIMENSIONS)
    assert progress["dimension_scores"]["Disciplina e Organização"] > 4.0


@pytest.mark.asyncio
async def test_resubmitting_replaces_the_choice_instead_of_duplicating(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    """Reenviar o teste não pode acumular escolhas e distorcer o perfil."""
    # Arrange
    question = seeded_questionnaire.questions[0]
    first, second = question.options[0], question.options[1]
    url = f"/api/v1/questionnaires/{seeded_questionnaire.id}/answers"

    # Act
    await authenticated_client.post(
        url, json={"answers": [{"question_id": str(question.id), "selected_option_id": str(first.id)}]}
    )
    await authenticated_client.post(
        url, json={"answers": [{"question_id": str(question.id), "selected_option_id": str(second.id)}]}
    )

    answers = await authenticated_client.get(f"/api/v1/questionnaires/{seeded_questionnaire.id}/my-answers")

    # Assert
    assert answers.status_code == 200
    assert len(answers.json()) == 1
    assert answers.json()[0]["selected_option_id"] == str(second.id)


@pytest.mark.asyncio
async def test_submit_rejects_question_from_another_questionnaire(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire, db_session: AsyncSession
):
    # Arrange
    other = Questionnaire(title="Outro instrumento", description=None)
    db_session.add(other)
    await db_session.commit()

    payload = {
        "answers": [
            {
                "question_id": str(uuid.uuid4()),
                "selected_option_id": str(seeded_questionnaire.questions[0].options[0].id),
            }
        ]
    }

    # Act
    response = await authenticated_client.post(
        f"/api/v1/questionnaires/{seeded_questionnaire.id}/answers", json=payload
    )

    # Assert
    assert response.status_code == 400
    assert "não pertencem" in response.json()["detail"]


@pytest.mark.asyncio
async def test_submit_rejects_option_from_another_scenario(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    """Alternativa de outro cenário aplicaria cargas erradas ao perfil."""
    # Arrange
    question = seeded_questionnaire.questions[0]
    foreign_option = seeded_questionnaire.questions[1].options[0]
    payload = {"answers": [{"question_id": str(question.id), "selected_option_id": str(foreign_option.id)}]}

    # Act
    response = await authenticated_client.post(
        f"/api/v1/questionnaires/{seeded_questionnaire.id}/answers", json=payload
    )

    # Assert
    assert response.status_code == 400
    assert "não pertence ao cenário" in response.json()["detail"]


@pytest.mark.asyncio
async def test_submit_rejects_duplicate_question(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    # Arrange
    question = seeded_questionnaire.questions[0]
    payload = {
        "answers": [
            {"question_id": str(question.id), "selected_option_id": str(question.options[0].id)},
            {"question_id": str(question.id), "selected_option_id": str(question.options[1].id)},
        ]
    }

    # Act
    response = await authenticated_client.post(
        f"/api/v1/questionnaires/{seeded_questionnaire.id}/answers", json=payload
    )

    # Assert
    assert response.status_code == 400
    assert "Duplicated" in response.json()["detail"]


@pytest.mark.asyncio
async def test_submit_rejects_malformed_payload(authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire):
    # Arrange: falta selected_option_id
    payload = {"answers": [{"question_id": str(seeded_questionnaire.questions[0].id)}]}

    # Act
    response = await authenticated_client.post(
        f"/api/v1/questionnaires/{seeded_questionnaire.id}/answers", json=payload
    )

    # Assert
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_answers_unauthorized(async_client: AsyncClient, seeded_questionnaire: Questionnaire):
    # Act
    response = await async_client.post(
        f"/api/v1/questionnaires/{seeded_questionnaire.id}/answers",
        json={"answers": [{"question_id": str(uuid.uuid4()), "selected_option_id": str(uuid.uuid4())}]},
    )

    # Assert
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_seed_is_idempotent(db_session: AsyncSession):
    """O seed roda a cada subida da aplicação — não pode duplicar cenários,
    alternativas nem cargas."""
    # Act
    first = await seed_default_questionnaire(db_session)
    second = await seed_default_questionnaire(db_session)

    # Assert
    assert first.id == second.id
    assert len(second.questions) == len(SJT_SCENARIOS)
    for question in second.questions:
        assert len(question.options) == 4
        for option in question.options:
            assert len(option.loadings) == len(option.loadings_map())
