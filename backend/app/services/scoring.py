"""Conversão de respostas SJT em perfil Big Five e em soft skills.

Módulo puro: sem banco, sem HTTP. Toda a aritmética do instrumento vive aqui.

```
alternativas escolhidas  →  soma de cargas por fator  →  normalização  →  1–5
                                                                           ↓
                         10 soft skills  ←  combinação ponderada dos fatores
```

A normalização é o ponto delicado. Um escore bruto de fator não significa nada
sozinho: depende de quantas vezes aquele fator apareceu como alternativa no
instrumento. Por isso cada fator é normalizado contra o **mínimo e o máximo
teoricamente obteníveis naquele questionário** — quanto alguém marcaria se
escolhesse sempre a alternativa de maior (ou menor) carga naquele fator. O
resultado cai em 1–5, a mesma escala que os limiares de `soft_skills.py` usam.
"""

from dataclasses import dataclass

from app.core.big_five import SOFT_SKILL_LOADINGS, TRAITS
from app.core.soft_skills import SCALE_MAX, SCALE_MIN


@dataclass(frozen=True)
class ScoredOption:
    """Alternativa escolhida, reduzida ao que o cálculo precisa."""

    question_id: object
    loadings: dict[str, float]


@dataclass(frozen=True)
class ItemBounds:
    """Cargas mínima, média e máxima de cada fator entre as alternativas de um item.

    A média é o que ancora o ponto médio da escala: é o escore esperado de quem
    responde sem preferência por aquele traço.
    """

    question_id: object
    min_by_trait: dict[str, float]
    mean_by_trait: dict[str, float]
    max_by_trait: dict[str, float]


def item_bounds(question_id: object, option_loadings: list[dict[str, float]]) -> ItemBounds:
    """Extremos e valor esperado de um item, fator a fator.

    Uma alternativa que não menciona o fator conta como carga 0 — não escolher a
    conduta associada àquele traço é, em si, informação.
    """
    min_by_trait: dict[str, float] = {}
    mean_by_trait: dict[str, float] = {}
    max_by_trait: dict[str, float] = {}

    for trait in TRAITS:
        values = [loadings.get(trait, 0.0) for loadings in option_loadings]
        if not values:
            continue
        min_by_trait[trait] = min(values)
        mean_by_trait[trait] = sum(values) / len(values)
        max_by_trait[trait] = max(values)

    return ItemBounds(
        question_id=question_id,
        min_by_trait=min_by_trait,
        mean_by_trait=mean_by_trait,
        max_by_trait=max_by_trait,
    )


def big_five_profile(chosen: list[ScoredOption], bounds: list[ItemBounds]) -> dict[str, float]:
    """Perfil Big Five em escala 1–5.

    Só considera os itens efetivamente respondidos: um questionário pela metade
    produz um perfil parcial, não um perfil enviesado para baixo.
    """
    if not chosen:
        return {}

    answered = {option.question_id for option in chosen}
    relevant = [b for b in bounds if b.question_id in answered]
    if not relevant:
        return {}

    profile: dict[str, float] = {}
    midpoint = (SCALE_MIN + SCALE_MAX) / 2
    half_span = (SCALE_MAX - SCALE_MIN) / 2

    for trait in TRAITS:
        raw = sum(option.loadings.get(trait, 0.0) for option in chosen)
        floor = sum(b.min_by_trait.get(trait, 0.0) for b in relevant)
        expected = sum(b.mean_by_trait.get(trait, 0.0) for b in relevant)
        ceiling = sum(b.max_by_trait.get(trait, 0.0) for b in relevant)

        if ceiling - floor <= 1e-9:
            # O fator não varia neste recorte de itens: não há informação sobre
            # ele. Marcar o ponto médio seria inventar dado — melhor omitir.
            continue

        # Ancoragem no nível de acaso. Normalizar contra o extremo teórico
        # transformaria a escala numa medida de *exclusividade* de traço: só quem
        # escolhe a conduta daquele fator em todos os 20 itens chegaria perto do
        # topo, e qualquer pessoa com preferências mistas — isto é, qualquer
        # pessoa real — cairia no piso em quase tudo. Com o ponto médio ancorado
        # no escore esperado ao acaso, 3.0 passa a significar "escolhe condutas
        # deste traço na frequência que o acaso produziria", 5.0 "sempre" e
        # 1.0 "nunca".
        if raw >= expected:
            headroom = ceiling - expected
            offset = half_span * ((raw - expected) / headroom) if headroom > 1e-9 else 0.0
        else:
            headroom = expected - floor
            offset = -half_span * ((expected - raw) / headroom) if headroom > 1e-9 else 0.0

        profile[trait] = round(max(SCALE_MIN, min(SCALE_MAX, midpoint + offset)), 2)

    return profile


def soft_skills_from_traits(trait_profile: dict[str, float]) -> dict[str, float]:
    """Deriva as 10 competências observáveis a partir dos cinco fatores.

    Como os pesos de cada competência somam 1.0, o resultado permanece em 1–5.
    Se algum fator de uma competência estiver ausente, os pesos presentes são
    renormalizados — a competência sai com menos sustentação, não distorcida.
    """
    skills: dict[str, float] = {}

    for skill, loadings in SOFT_SKILL_LOADINGS.items():
        available = {t: w for t, w in loadings.items() if t in trait_profile}
        total_weight = sum(available.values())
        if total_weight <= 0:
            continue
        skills[skill] = round(sum(trait_profile[t] * w for t, w in available.items()) / total_weight, 2)

    return skills


def profile_from_selection(
    chosen: list[ScoredOption], bounds: list[ItemBounds]
) -> tuple[dict[str, float], dict[str, float]]:
    """Atalho para o par (fatores Big Five, soft skills)."""
    traits = big_five_profile(chosen, bounds)
    return traits, soft_skills_from_traits(traits)
