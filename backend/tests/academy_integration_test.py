"""Testes da integração com o OxeTech Academy.

Cobrem as três camadas sem tocar a rede: o cliente é exercido com um transporte
HTTP mockado, e o simulador roda contra o banco SQLite em memória do conftest,
com o instrumento padrão já semeado.
"""

import httpx
import pytest

from app.integrations.academy.client import MAX_PER_PAGE, AcademyAPIError, AcademyClient
from app.integrations.academy.roster import synthetic_talent_pool
from app.integrations.academy.schemas import AcademyAluno
from app.integrations.academy.simulator import (
    AcademyMatchSimulator,
    answers_for_preference,
    derive_trait_preference,
)

# ----------------------------------------------------------------------
# Schemas — normalização tolerante
# ----------------------------------------------------------------------


def test_aluno_normalizes_tecnologias_list():
    aluno = AcademyAluno.from_payload({"id": 1, "nome": "  Fulana  ", "tecnologias": ["Python", " React "]})
    assert aluno.nome == "Fulana"
    assert aluno.techs == ["Python", "React"]


def test_aluno_normalizes_tecnologia_string_and_objects():
    from_string = AcademyAluno.from_payload({"id": 2, "tecnologia": "Go, Rust"})
    from_objects = AcademyAluno.from_payload({"id": 3, "skills": [{"nome": "Java"}, {"name": "Kotlin"}]})
    assert from_string.techs == ["Go", "Rust"]
    assert from_objects.techs == ["Java", "Kotlin"]
    # Sem nome, o display cai para um rótulo estável.
    assert from_string.display_name == "Aluno #2"


def test_aluno_survives_unknown_extra_fields():
    aluno = AcademyAluno.from_payload({"id": 9, "nome": "Ciclana", "campo_novo": {"x": 1}})
    assert aluno.id == 9 and aluno.techs == []


# ----------------------------------------------------------------------
# Cliente HTTP — com transporte mockado
# ----------------------------------------------------------------------


def _mock_transport(handler):
    return httpx.MockTransport(handler)


async def test_client_ping_and_stats():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer tok"
        if request.url.path.endswith("/ping"):
            return httpx.Response(200, json={"ok": True, "aluno": {"id": 1, "nome": "X"}})
        if request.url.path.endswith("/stats"):
            return httpx.Response(200, json={"empresas_ativas": 4, "alunos_disponiveis": 12})
        return httpx.Response(404, json={})

    async with AcademyClient("tok", transport=_mock_transport(handler)) as client:
        assert (await client.ping())["ok"] is True
        stats = await client.stats()
        assert stats.empresas_ativas == 4
        assert stats.alunos_disponiveis == 12


async def test_client_paginates_alunos():
    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", 1))
        # Confirma que o cliente respeita o teto de per_page da API.
        assert int(request.url.params["per_page"]) <= MAX_PER_PAGE
        if page == 1:
            return httpx.Response(
                200,
                json={
                    "data": [{"id": 1, "nome": "A", "tecnologias": ["Python"]}],
                    "meta": {"page": 1, "per_page": 1, "total": 2, "total_pages": 2},
                },
            )
        return httpx.Response(
            200,
            json={
                "data": [{"id": 2, "nome": "B", "tecnologia": "Go"}],
                "meta": {"page": 2, "per_page": 1, "total": 2, "total_pages": 2},
            },
        )

    async with AcademyClient("tok", transport=_mock_transport(handler)) as client:
        alunos = await client.list_alunos_all(max_items=10, disponivel=True)
    assert [a.id for a in alunos] == [1, 2]
    assert alunos[0].techs == ["Python"]


async def test_client_raises_on_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    async with AcademyClient("bad", transport=_mock_transport(handler)) as client:
        with pytest.raises(AcademyAPIError) as exc:
            await client.stats()
    assert exc.value.status_code == 401


def test_client_requires_token():
    with pytest.raises(AcademyAPIError):
        AcademyClient("")


# ----------------------------------------------------------------------
# Perfis determinísticos
# ----------------------------------------------------------------------


def test_trait_preference_is_deterministic_and_varied():
    pool = synthetic_talent_pool()
    first = derive_trait_preference(pool[0])
    again = derive_trait_preference(pool[0])
    other = derive_trait_preference(pool[1])
    assert first == again  # mesmo aluno → mesmo perfil
    assert first != other  # alunos diferentes → perfis diferentes


# ----------------------------------------------------------------------
# Simulador — fluxo completo contra o banco
# ----------------------------------------------------------------------


async def test_simulator_ranks_and_covers_gaps(db_session, seeded_questionnaire):
    pool = synthetic_talent_pool()
    simulator = AcademyMatchSimulator(db_session, seeded_questionnaire)

    result = await simulator.run(pool, team_size=6, source="synthetic", seed=42)

    # Time montado e diagnosticado.
    assert len(result.team_members) == 6
    assert result.respondent_count == 6
    assert result.team_scores  # perfil não-vazio

    # Todo o restante do pool virou candidato ranqueado.
    assert len(result.ranked) == len(pool) - 6

    # Ranking em ordem não-crescente de fit.
    fits = [c.fit_score for c in result.ranked]
    assert fits == sorted(fits, reverse=True)

    # O melhor encaixe existe e tem o maior fit.
    best = result.best
    assert best is not None
    assert best.fit_score == max(fits)


async def test_simulator_best_candidate_regularizes_radar(db_session, seeded_questionnaire):
    """O candidato mais bem ranqueado não deve piorar a regularidade do radar."""
    pool = synthetic_talent_pool()
    simulator = AcademyMatchSimulator(db_session, seeded_questionnaire)
    result = await simulator.run(pool, team_size=6, source="synthetic", seed=1)

    best = result.best
    assert best is not None
    # Contratar o melhor encaixe deixa o radar do time ao menos tão regular
    # quanto antes — nunca mais disperso.
    assert best.dispersion_after <= result.dispersion_before + 1e-9


async def test_simulator_is_reproducible(db_session, seeded_questionnaire):
    pool = synthetic_talent_pool()
    sim = AcademyMatchSimulator(db_session, seeded_questionnaire)

    # Duas execuções com a mesma semente: mesma composição de time e mesma ordem
    # de ranqueamento. Perfis vêm de hash do id, então nada depende do relógio.
    first = await sim.run(pool, team_size=5, source="synthetic", seed=7)
    second = await sim.run(pool, team_size=5, source="synthetic", seed=7)

    assert first.team_members == second.team_members
    assert [c.aluno_id for c in first.ranked] == [c.aluno_id for c in second.ranked]
    assert [c.fit_score for c in first.ranked] == [c.fit_score for c in second.ranked]


async def test_simulator_rejects_tiny_pool(db_session, seeded_questionnaire):
    simulator = AcademyMatchSimulator(db_session, seeded_questionnaire)
    with pytest.raises(ValueError):
        await simulator.run(synthetic_talent_pool(3), team_size=6, source="synthetic")


def test_answers_cover_every_question(seeded_questionnaire):
    pool = synthetic_talent_pool()
    prefs = derive_trait_preference(pool[0])
    answers = answers_for_preference(list(seeded_questionnaire.questions), prefs, pool[0].id)
    assert len(answers) == len(seeded_questionnaire.questions)
    assert all(a.elapsed_ms is not None for a in answers)
