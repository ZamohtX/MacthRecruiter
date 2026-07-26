"""Camada de jogo do instrumento: níveis, ritmo e tempo de resposta.

O que estes testes protegem, além do óbvio: que a gamificação **não** vaze a
chave de correção. Um rótulo de nível que citasse o traço medido faria o
respondente escolher pelo rótulo, que é exatamente o que o formato SJT existe
para evitar.
"""

import json

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.big_five import SJT_SCENARIOS, TRAITS
from app.core.gamification import (
    ESTIMATED_SECONDS_PER_SCENARIO,
    LEVEL_SIZE,
    build_levels,
    estimated_seconds,
    level_index_for,
)
from app.models.questionnaire import AssessmentAnswer, Questionnaire
from app.models.user import User


# --------------------------------------------------------------------- níveis
def test_build_levels_divides_the_instrument_into_blocks_of_five():
    # Act
    levels = build_levels(20)

    # Assert
    assert [level.question_count for level in levels] == [5, 5, 5, 5]
    assert [level.first_position for level in levels] == [0, 5, 10, 15]
    assert levels[-1].last_position == 19
    assert all(level.title and level.subtitle for level in levels)


def test_build_levels_keeps_the_remainder_in_a_shorter_last_level():
    """Um instrumento de 22 cenários termina em bloco de 2.

    Arredondar para baixo esconderia dois itens do teste — perder medida é pior
    que um nível curto.
    """
    # Act
    levels = build_levels(22)

    # Assert
    assert [level.question_count for level in levels] == [5, 5, 5, 5, 2]
    assert sum(level.question_count for level in levels) == 22


def test_build_levels_labels_blocks_beyond_the_written_specs():
    """A rotação de itens (§10.4) vai aumentar o banco além dos rótulos escritos.

    Sem o fallback, o instrumento inteiro quebraria por falta de um título.
    """
    # Act
    levels = build_levels(60)

    # Assert
    assert len(levels) == 12
    assert all(level.title for level in levels)


def test_build_levels_of_an_empty_instrument_is_empty():
    assert build_levels(0) == ()


@pytest.mark.parametrize(
    ("ordinal", "expected"),
    [(0, 0), (4, 0), (5, 1), (9, 1), (10, 2), (19, 3)],
)
def test_level_index_follows_display_order(ordinal: int, expected: int):
    assert level_index_for(ordinal) == expected


def test_estimated_seconds_scales_with_the_number_of_scenarios():
    assert estimated_seconds(LEVEL_SIZE) == LEVEL_SIZE * ESTIMATED_SECONDS_PER_SCENARIO
    assert estimated_seconds(0) == 0


# ------------------------------------------------------- níveis na API pública
@pytest.mark.asyncio
async def test_questionnaire_exposes_levels_and_tags_each_scenario(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    # Act
    response = await authenticated_client.get("/api/v1/questionnaires/default")

    # Assert
    data = response.json()
    assert [level["question_count"] for level in data["levels"]] == [5, 5, 5, 5]
    assert data["estimated_minutes"] == round(len(SJT_SCENARIOS) * ESTIMATED_SECONDS_PER_SCENARIO / 60)

    # O nível de cada cenário casa com o bloco anunciado no cabeçalho.
    assert [q["level"] for q in data["questions"]] == [level_index_for(i) for i in range(len(SJT_SCENARIOS))]


@pytest.mark.asyncio
async def test_level_labels_never_name_the_trait_they_measure(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    """Um nível chamado "Disciplina" entregaria a chave de correção do bloco."""
    # Act
    response = await authenticated_client.get("/api/v1/questionnaires/default")

    # Assert
    levels_payload = json.dumps(response.json()["levels"], ensure_ascii=False)
    for trait in TRAITS:
        assert trait not in levels_payload


# ------------------------------------------------------------------- progresso
@pytest.mark.asyncio
async def test_progress_starts_with_every_level_empty(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    # Act
    response = await authenticated_client.get(f"/api/v1/questionnaires/{seeded_questionnaire.id}/my-progress")

    # Assert
    data = response.json()
    assert data["current_level"] == 0
    assert [level["answered_questions"] for level in data["levels"]] == [0, 0, 0, 0]
    assert not any(level["is_complete"] for level in data["levels"])
    assert data["elapsed_seconds"] is None
    assert data["estimated_seconds_remaining"] == len(SJT_SCENARIOS) * ESTIMATED_SECONDS_PER_SCENARIO


@pytest.mark.asyncio
async def test_finishing_a_block_completes_the_level_and_moves_the_pointer(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    # Arrange: responde exatamente os cinco cenários do primeiro nível.
    questions = seeded_questionnaire.questions[:LEVEL_SIZE]
    payload = [
        {"question_id": str(q.id), "selected_option_id": str(q.options[0].id), "elapsed_ms": 20_000} for q in questions
    ]

    # Act
    response = await authenticated_client.post(
        f"/api/v1/questionnaires/{seeded_questionnaire.id}/answers", json={"answers": payload}
    )

    # Assert
    progress = response.json()["progress"]
    assert progress["levels"][0]["is_complete"] is True
    assert progress["levels"][0]["answered_questions"] == LEVEL_SIZE
    assert progress["levels"][1]["answered_questions"] == 0
    assert progress["current_level"] == 1
    assert progress["elapsed_seconds"] == 100  # 5 × 20 s
    remaining = len(SJT_SCENARIOS) - LEVEL_SIZE
    assert progress["estimated_seconds_remaining"] == remaining * ESTIMATED_SECONDS_PER_SCENARIO


@pytest.mark.asyncio
async def test_answering_out_of_order_completes_only_the_touched_level(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    """A ordem de resposta é livre — o nível concluído é o que foi preenchido.

    A API nunca bloqueou responder um item fora de ordem, e travar isso
    quebraria a retomada de um teste respondido em etapas.
    """
    # Arrange: só o terceiro bloco.
    questions = seeded_questionnaire.questions[2 * LEVEL_SIZE : 3 * LEVEL_SIZE]
    payload = [{"question_id": str(q.id), "selected_option_id": str(q.options[0].id)} for q in questions]

    # Act
    response = await authenticated_client.post(
        f"/api/v1/questionnaires/{seeded_questionnaire.id}/answers", json={"answers": payload}
    )

    # Assert
    progress = response.json()["progress"]
    assert [level["is_complete"] for level in progress["levels"]] == [False, False, True, False]
    assert progress["current_level"] == 0  # retoma no primeiro bloco em aberto


@pytest.mark.asyncio
async def test_completed_assessment_points_at_the_last_level(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    # Arrange
    payload = [
        {"question_id": str(q.id), "selected_option_id": str(q.options[0].id)} for q in seeded_questionnaire.questions
    ]

    # Act
    response = await authenticated_client.post(
        f"/api/v1/questionnaires/{seeded_questionnaire.id}/answers", json={"answers": payload}
    )

    # Assert
    progress = response.json()["progress"]
    assert progress["is_complete"] is True
    assert all(level["is_complete"] for level in progress["levels"])
    assert progress["current_level"] == len(progress["levels"]) - 1
    assert progress["estimated_seconds_remaining"] == 0


# --------------------------------------------------------------- tempo medido
@pytest.mark.asyncio
async def test_elapsed_time_is_optional_for_api_clients(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    """Script de demo e carga em lote não têm medida de tempo.

    Exigir o campo faria esses clientes inventarem número, contaminando
    exatamente a estatística que a coluna existe para levantar.
    """
    # Arrange
    question = seeded_questionnaire.questions[0]

    # Act
    response = await authenticated_client.post(
        f"/api/v1/questionnaires/{seeded_questionnaire.id}/answers",
        json={"answers": [{"question_id": str(question.id), "selected_option_id": str(question.options[0].id)}]},
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["progress"]["elapsed_seconds"] is None


@pytest.mark.asyncio
async def test_elapsed_time_sums_only_measured_answers(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    """Somar zero pelas respostas sem medida produziria um teste rápido falso."""
    # Arrange
    first, second = seeded_questionnaire.questions[0], seeded_questionnaire.questions[1]

    # Act
    response = await authenticated_client.post(
        f"/api/v1/questionnaires/{seeded_questionnaire.id}/answers",
        json={
            "answers": [
                {"question_id": str(first.id), "selected_option_id": str(first.options[0].id), "elapsed_ms": 30_000},
                {"question_id": str(second.id), "selected_option_id": str(second.options[0].id)},
            ]
        },
    )

    # Assert
    assert response.json()["progress"]["elapsed_seconds"] == 30


@pytest.mark.asyncio
async def test_revising_an_answer_keeps_the_first_measured_time(
    authenticated_client: AsyncClient,
    seeded_questionnaire: Questionnaire,
    db_session: AsyncSession,
    recruiter_user: User,
):
    """Revisar uma escolha já lida leva segundos.

    Sobrescrever o tempo encurtaria artificialmente a duração do teste — o
    número que a coluna existe para medir.
    """
    # Arrange
    question = seeded_questionnaire.questions[0]
    url = f"/api/v1/questionnaires/{seeded_questionnaire.id}/answers"
    await authenticated_client.post(
        url,
        json={
            "answers": [
                {
                    "question_id": str(question.id),
                    "selected_option_id": str(question.options[0].id),
                    "elapsed_ms": 45_000,
                }
            ]
        },
    )

    # Act: troca a conduta escolhida, agora em 2 segundos.
    await authenticated_client.post(
        url,
        json={
            "answers": [
                {
                    "question_id": str(question.id),
                    "selected_option_id": str(question.options[1].id),
                    "elapsed_ms": 2_000,
                }
            ]
        },
    )

    # Assert
    stored = await db_session.execute(
        select(AssessmentAnswer).where(
            AssessmentAnswer.user_id == recruiter_user.id,
            AssessmentAnswer.question_id == question.id,
        )
    )
    answer = stored.scalar_one()
    assert answer.selected_option_id == question.options[1].id
    assert answer.elapsed_ms == 45_000


@pytest.mark.asyncio
async def test_negative_elapsed_time_is_rejected(
    authenticated_client: AsyncClient, seeded_questionnaire: Questionnaire
):
    # Arrange
    question = seeded_questionnaire.questions[0]

    # Act
    response = await authenticated_client.post(
        f"/api/v1/questionnaires/{seeded_questionnaire.id}/answers",
        json={
            "answers": [
                {"question_id": str(question.id), "selected_option_id": str(question.options[0].id), "elapsed_ms": -1}
            ]
        },
    )

    # Assert
    assert response.status_code == 422
