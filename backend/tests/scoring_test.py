"""Testes da conversão SJT → Big Five → soft skills.

Módulo puro: sem banco, sem HTTP. É a aritmética do instrumento — se ela estiver
errada, todo o resto do produto ranqueia ruído com aparência de método.
"""

from app.core.big_five import SJT_SCENARIOS, SOFT_SKILL_LOADINGS, TRAITS, Trait
from app.core.soft_skills import DIMENSIONS, SCALE_MAX, SCALE_MIN
from app.services.scoring import (
    ItemBounds,
    ScoredOption,
    big_five_profile,
    item_bounds,
    soft_skills_from_traits,
)


def _bounds_from_scenarios():
    return [item_bounds(i, [dict(o.loadings) for o in s.options]) for i, s in enumerate(SJT_SCENARIOS)]


def _answer_all(trait_preference: dict[str, float]) -> list[ScoredOption]:
    """Simula alguém que escolhe sempre a conduta mais alinhada à preferência."""
    chosen = []
    for i, scenario in enumerate(SJT_SCENARIOS):
        best = max(
            scenario.options,
            key=lambda o: sum(trait_preference.get(t, 0.0) * w for t, w in o.loadings.items()),
        )
        chosen.append(ScoredOption(question_id=i, loadings=dict(best.loadings)))
    return chosen


# ---------------------------------------------------------------------------
# Integridade do instrumento
# ---------------------------------------------------------------------------


def test_every_soft_skill_has_trait_loadings_that_sum_to_one():
    """Pesos somando 1.0 é o que mantém a competência derivada na escala 1–5."""
    assert set(SOFT_SKILL_LOADINGS) == set(DIMENSIONS)
    for skill, loadings in SOFT_SKILL_LOADINGS.items():
        assert abs(sum(loadings.values()) - 1.0) < 1e-9, f"{skill} não soma 1.0"
        assert set(loadings).issubset(set(TRAITS)), f"{skill} referencia fator inexistente"


def test_every_option_loads_on_at_least_one_trait():
    for scenario in SJT_SCENARIOS:
        for option in scenario.options:
            assert option.loadings, f"alternativa sem carga: {scenario.context} / {option.text}"
            assert set(option.loadings).issubset(set(TRAITS))
            assert all(0.0 <= w <= 1.0 for w in option.loadings.values())


def test_every_trait_is_measurable_across_the_instrument():
    """Um fator sem variação no banco de itens não é medido — sairia ausente do
    perfil e derrubaria as competências que dependem dele."""
    bounds = _bounds_from_scenarios()
    for trait in TRAITS:
        spread = sum(b.max_by_trait.get(trait, 0.0) - b.min_by_trait.get(trait, 0.0) for b in bounds)
        assert spread > 0, f"{trait} não varia em nenhum item"


def test_scenarios_offer_real_choice():
    """Todo cenário precisa de alternativas distintas com cargas distintas —
    alternativa obviamente melhor reintroduz a resposta socialmente desejável."""
    for scenario in SJT_SCENARIOS:
        assert len(scenario.options) >= 3
        texts = [o.text for o in scenario.options]
        assert len(set(texts)) == len(texts)
        primary = [max(o.loadings, key=o.loadings.get) for o in scenario.options]
        assert len(set(primary)) >= 3, f"cenário pouco discriminante: {scenario.context}"


# ---------------------------------------------------------------------------
# Pontuação
# ---------------------------------------------------------------------------


def test_consistent_choices_push_the_targeted_trait_to_the_top_of_the_scale():
    # Arrange: alguém que escolhe sempre a conduta mais conscienciosa
    chosen = _answer_all({Trait.CONSCIENCIOSIDADE: 1.0})

    # Act
    profile = big_five_profile(chosen, _bounds_from_scenarios())

    # Assert
    assert profile[Trait.CONSCIENCIOSIDADE] == SCALE_MAX
    assert all(SCALE_MIN <= v <= SCALE_MAX for v in profile.values())


def test_avoiding_a_trait_puts_it_at_the_bottom_of_the_scale():
    # Arrange: preferência negativa faz a pessoa fugir daquela conduta
    chosen = _answer_all({Trait.EXTROVERSAO: -1.0})

    # Act
    profile = big_five_profile(chosen, _bounds_from_scenarios())

    # Assert
    assert profile[Trait.EXTROVERSAO] == SCALE_MIN


def test_different_trait_preferences_produce_different_profiles():
    # Arrange
    bounds = _bounds_from_scenarios()

    # Act
    organized = big_five_profile(_answer_all({Trait.CONSCIENCIOSIDADE: 1.0}), bounds)
    explorer = big_five_profile(_answer_all({Trait.ABERTURA: 1.0}), bounds)

    # Assert
    assert organized[Trait.CONSCIENCIOSIDADE] > explorer[Trait.CONSCIENCIOSIDADE]
    assert explorer[Trait.ABERTURA] > organized[Trait.ABERTURA]


def test_empty_selection_returns_empty_profile():
    assert big_five_profile([], _bounds_from_scenarios()) == {}


def test_partial_answers_normalize_against_answered_items_only():
    """Responder metade do teste não pode rebaixar o perfil: a normalização usa
    apenas os itens efetivamente respondidos."""
    # Arrange
    bounds = _bounds_from_scenarios()
    full = _answer_all({Trait.CONSCIENCIOSIDADE: 1.0})
    half = full[:10]

    # Act
    profile = big_five_profile(half, bounds)

    # Assert
    assert profile[Trait.CONSCIENCIOSIDADE] == SCALE_MAX


def test_trait_with_no_variation_is_omitted_instead_of_guessed():
    # Arrange: item único em que Abertura tem a mesma carga em toda alternativa
    chosen = [ScoredOption(question_id=1, loadings={Trait.ABERTURA: 0.5, Trait.EXTROVERSAO: 1.0})]
    bounds = [
        ItemBounds(
            question_id=1,
            min_by_trait={Trait.ABERTURA: 0.5, Trait.EXTROVERSAO: 0.0},
            mean_by_trait={Trait.ABERTURA: 0.5, Trait.EXTROVERSAO: 0.5},
            max_by_trait={Trait.ABERTURA: 0.5, Trait.EXTROVERSAO: 1.0},
        )
    ]

    # Act
    profile = big_five_profile(chosen, bounds)

    # Assert
    assert Trait.ABERTURA not in profile
    assert profile[Trait.EXTROVERSAO] == SCALE_MAX


# ---------------------------------------------------------------------------
# Derivação das competências
# ---------------------------------------------------------------------------


def test_soft_skills_stay_within_the_scale_and_cover_every_dimension():
    # Arrange
    traits = {t: 3.0 for t in TRAITS}

    # Act
    skills = soft_skills_from_traits(traits)

    # Assert: fatores todos em 3.0 produzem competências todas em 3.0
    assert set(skills) == set(DIMENSIONS)
    assert all(v == 3.0 for v in skills.values())


def test_discipline_follows_conscientiousness():
    """Disciplina carrega 0.80 em Conscienciosidade — a competência tem que se
    mover junto com o fator que a sustenta."""
    # Arrange
    low = {t: 3.0 for t in TRAITS} | {Trait.CONSCIENCIOSIDADE: 1.0}
    high = {t: 3.0 for t in TRAITS} | {Trait.CONSCIENCIOSIDADE: 5.0}

    # Act & Assert
    assert soft_skills_from_traits(low)["Disciplina e Organização"] < 3.0
    assert soft_skills_from_traits(high)["Disciplina e Organização"] > 3.0


def test_missing_trait_renormalizes_remaining_weights():
    # Arrange: Criatividade carrega Abertura (0.75) e Extroversão (0.25)
    traits = {Trait.ABERTURA: 4.0}

    # Act
    skills = soft_skills_from_traits(traits)

    # Assert: sem Extroversão, o peso restante é renormalizado para 1.0
    assert skills["Criatividade e Inovação"] == 4.0


def test_empty_traits_produce_no_skills():
    assert soft_skills_from_traits({}) == {}
