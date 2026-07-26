"""Testes do motor de fit complementar.

Módulo puro: nada de banco ou HTTP. É a regra de negócio que diferencia o produto
de um ATS comum, então cada cenário abaixo descreve uma decisão de contratação
concreta.
"""

from app.core.soft_skills import Dimension
from app.services.fit_engine import (
    DimensionStatus,
    FitVerdict,
    classify_dimension,
    deficit_weight,
    evaluate_fit,
    profile_norms,
    simulate_team_average,
)

# Time forte em análise e criatividade, fraco em disciplina e comunicação.
UNBALANCED_TEAM = {
    Dimension.COMUNICACAO: 2.4,
    Dimension.DISCIPLINA: 2.1,
    Dimension.ANALITICO: 4.6,
    Dimension.CRIATIVIDADE: 4.5,
}


def test_simulate_team_average_matches_documented_formula():
    # Arrange: time de 4 pessoas com média 3.0, candidato com 5.0
    # Act
    result = simulate_team_average(team_score=3.0, candidate_score=5.0, team_size=4)

    # Assert: (3.0 * 4 + 5.0) / 5 = 3.4
    assert result == 3.4


def test_simulate_team_average_with_empty_team_returns_candidate_score():
    assert simulate_team_average(team_score=0.0, candidate_score=4.2, team_size=0) == 4.2


def test_classify_dimension_is_relative_to_the_team_profile():
    """Lacuna e força são posições dentro do perfil do time, não notas absolutas."""
    # Arrange: centro 3.35, dispersão ~1.05 → banda de meio desvio ≈ ±0.53
    norms = profile_norms(UNBALANCED_TEAM)

    # Act & Assert
    assert classify_dimension(2.1, norms) == DimensionStatus.GAP
    assert classify_dimension(4.6, norms) == DimensionStatus.STRENGTH
    assert classify_dimension(norms.center, norms) == DimensionStatus.ADEQUATE


def test_uniform_team_has_neither_gaps_nor_strengths():
    """Time igualmente forte em tudo não tem o que priorizar por complementaridade."""
    # Arrange
    norms = profile_norms({"A": 3.0, "B": 3.0, "C": 3.05})

    # Assert
    assert norms.is_uniform
    assert classify_dimension(3.0, norms) == DimensionStatus.ADEQUATE
    assert deficit_weight(3.0, norms) == 0.0


def test_deficit_weight_grows_with_distance_below_the_team_center():
    # Arrange
    norms = profile_norms(UNBALANCED_TEAM)

    # Act & Assert
    assert deficit_weight(norms.center, norms) == 0.0
    assert deficit_weight(4.6, norms) == 0.0
    assert deficit_weight(2.1, norms) > deficit_weight(2.4, norms) > 0.0


def test_complementary_candidate_scores_higher_than_redundant_one():
    """O caso central do produto: dois candidatos igualmente 'bons' na média,
    mas apenas um cobre a lacuna do time."""
    # Arrange
    complementary = {
        Dimension.COMUNICACAO: 4.6,
        Dimension.DISCIPLINA: 4.7,
        Dimension.ANALITICO: 3.0,
        Dimension.CRIATIVIDADE: 3.0,
    }
    redundant = {
        Dimension.COMUNICACAO: 3.0,
        Dimension.DISCIPLINA: 3.0,
        Dimension.ANALITICO: 4.8,
        Dimension.CRIATIVIDADE: 4.7,
    }

    # Act
    good = evaluate_fit(UNBALANCED_TEAM, complementary, team_size=5, respondent_count=5)
    bad = evaluate_fit(UNBALANCED_TEAM, redundant, team_size=5, respondent_count=5)

    # Assert
    assert good.complementary_fit_score > bad.complementary_fit_score
    assert good.verdict == FitVerdict.COMPLEMENTARY
    assert set(good.gaps_filled) == {Dimension.COMUNICACAO, Dimension.DISCIPLINA}


def test_excessive_supplementary_fit_is_flagged():
    """Candidato espelho do time: reforça as forças e mal move as lacunas.

    Fica acima do piso mínimo absoluto em todas as dimensões — sem isso o
    veredito seria `BELOW_MINIMUM`, que tem precedência. O que se testa aqui é a
    redundância isolada, não a violação de piso.
    """
    # Arrange: perfil praticamente idêntico ao do time
    mirror = {
        Dimension.COMUNICACAO: 2.5,
        Dimension.DISCIPLINA: 2.6,
        Dimension.ANALITICO: 4.8,
        Dimension.CRIATIVIDADE: 4.7,
    }

    # Act
    result = evaluate_fit(UNBALANCED_TEAM, mirror, team_size=6, respondent_count=6)

    # Assert
    assert result.verdict == FitVerdict.EXCESSIVE_SUPPLEMENTARY
    assert result.supplementary_fit_index > 85.0
    assert result.redundancy is not None and result.redundancy >= 0.7
    assert any("suplementar em excesso" in flag for flag in result.risk_flags)
    assert set(result.overlaps) == {Dimension.ANALITICO, Dimension.CRIATIVIDADE}


def test_candidate_leaving_an_absent_competency_uncovered_is_capped():
    """Guarda-corpo: a competência não existe no time e continua não existindo."""
    # Arrange: time abaixo do piso absoluto em Comunicação e Disciplina
    team_without_the_basics = {
        Dimension.COMUNICACAO: 1.6,
        Dimension.DISCIPLINA: 1.4,
        Dimension.ANALITICO: 4.6,
        Dimension.CRIATIVIDADE: 4.5,
    }
    weak_where_it_hurts = {
        Dimension.COMUNICACAO: 1.5,
        Dimension.DISCIPLINA: 1.2,
        Dimension.ANALITICO: 5.0,
        Dimension.CRIATIVIDADE: 5.0,
    }

    # Act
    result = evaluate_fit(team_without_the_basics, weak_where_it_hurts, team_size=5, respondent_count=5)

    # Assert
    assert result.verdict == FitVerdict.BELOW_MINIMUM
    assert result.complementary_fit_score <= 55.0
    assert any("fica descoberta" in flag for flag in result.risk_flags)
    assert Dimension.COMUNICACAO in result.gaps_missed


def test_verdict_is_insufficient_data_when_nobody_answered():
    # Arrange: nenhum integrante respondeu — não existe perfil de time
    candidate = {Dimension.COMUNICACAO: 4.0, Dimension.DISCIPLINA: 4.0}

    # Act
    result = evaluate_fit({}, candidate, team_size=3, respondent_count=0)

    # Assert
    assert result.verdict == FitVerdict.INSUFFICIENT_TEAM_DATA
    assert any("Nenhum integrante" in flag for flag in result.risk_flags)


def test_supplementary_index_is_maximum_for_identical_profile():
    # Arrange
    profile = {Dimension.COMUNICACAO: 3.0, Dimension.DISCIPLINA: 4.0}

    # Act
    result = evaluate_fit(profile, dict(profile), team_size=4, respondent_count=4)

    # Assert
    assert result.supplementary_fit_index == 100.0


def test_simulation_moves_team_average_toward_candidate():
    # Arrange
    candidate = {
        Dimension.COMUNICACAO: 5.0,
        Dimension.DISCIPLINA: 5.0,
        Dimension.ANALITICO: 4.6,
        Dimension.CRIATIVIDADE: 4.5,
    }

    # Act
    result = evaluate_fit(UNBALANCED_TEAM, candidate, team_size=4, respondent_count=4)

    # Assert: dimensões com lacuna sobem, forças ficam estáveis
    assert result.score_deltas[Dimension.COMUNICACAO] > 0
    assert result.score_deltas[Dimension.DISCIPLINA] > 0
    assert result.score_deltas[Dimension.ANALITICO] == 0.0


def test_insights_explain_every_dimension():
    # Arrange
    candidate = {d: 4.0 for d in UNBALANCED_TEAM}

    # Act
    result = evaluate_fit(UNBALANCED_TEAM, candidate, team_size=5, respondent_count=5)

    # Assert
    assert {i.dimension for i in result.insights} == set(UNBALANCED_TEAM)
    assert all(i.explanation for i in result.insights)


def test_lifting_a_gap_without_reaching_the_team_center_is_not_a_filled_gap():
    """Pontuar acima de um time fraco não basta: se o candidato fica abaixo do
    nível médio do próprio time, a lacuna continua aberta após a contratação."""
    # Arrange: time em 2.1 na Disciplina, centro do perfil em ~3.35;
    # candidato em 3.0 melhora a média mas não chega ao centro
    candidate = {
        Dimension.DISCIPLINA: 3.0,
        Dimension.ANALITICO: 4.8,
        Dimension.CRIATIVIDADE: 4.7,
        Dimension.COMUNICACAO: 3.0,
    }

    # Act
    result = evaluate_fit(UNBALANCED_TEAM, candidate, team_size=4, respondent_count=4)

    # Assert
    assert Dimension.DISCIPLINA not in result.gaps_filled
    assert Dimension.DISCIPLINA in result.gaps_missed
    assert result.score_deltas[Dimension.DISCIPLINA] > 0  # a média sobe

    insight = next(i for i in result.insights if i.dimension == Dimension.DISCIPLINA)
    assert insight.contribution == "PARTIAL_LIFT"
    assert "segue aberta" in insight.explanation
