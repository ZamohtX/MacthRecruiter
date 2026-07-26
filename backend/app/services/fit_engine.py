"""Motor de cálculo do fit complementar.

Módulo puro (sem I/O, sem banco, sem FastAPI) para que a regra de negócio central
do produto seja testável isoladamente e auditável linha a linha — requisito de
explicabilidade descrito em `docs/visao-de-negocio.md` §Etapa 2 e §10.1.

Conceitos:

* **Fit suplementar** — o quanto o candidato *se parece* com o time. Alto demais
  significa contratar mais do mesmo: o time fica maior, não melhor. É o problema
  que este produto existe para evitar.
* **Fit complementar** — o quanto o candidato *cobre as lacunas* do time sem
  apenas reforçar o que já é forte. É a métrica que ranqueia candidatos.
"""

from dataclasses import dataclass, field
from statistics import pstdev

from app.core.soft_skills import (
    MIN_CANDIDATE_FLOOR,
    MIN_MEANINGFUL_SPREAD,
    RELATIVE_BAND,
    SCALE_MAX,
    SCALE_MIN,
)

# Pesos dos componentes do score final. Somam 1.0; se um componente não for
# calculável (ex.: time sem nenhuma lacuna), os pesos restantes são renormalizados.
WEIGHT_GAP_COVERAGE = 0.55
WEIGHT_BALANCE_GAIN = 0.20
WEIGHT_NON_REDUNDANCY = 0.25

# Limiares que disparam o veredito de fit suplementar excessivo.
EXCESSIVE_REDUNDANCY = 0.70
LOW_GAP_COVERAGE = 0.35

# Teto aplicado ao score quando o candidato fica abaixo do piso mínimo numa
# dimensão que já é lacuna do time — nesse caso a contratação aprofunda o buraco.
CRITICAL_VIOLATION_CAP = 55.0


class DimensionStatus:
    GAP = "GAP"
    ADEQUATE = "ADEQUATE"
    STRENGTH = "STRENGTH"


class FitVerdict:
    COMPLEMENTARY = "COMPLEMENTARY"
    BALANCED = "BALANCED"
    EXCESSIVE_SUPPLEMENTARY = "EXCESSIVE_SUPPLEMENTARY"
    BELOW_MINIMUM = "BELOW_MINIMUM"
    INSUFFICIENT_TEAM_DATA = "INSUFFICIENT_TEAM_DATA"


@dataclass
class DimensionInsight:
    dimension: str
    team_score: float
    candidate_score: float
    simulated_score: float
    delta: float
    status: str
    contribution: str
    explanation: str


@dataclass
class FitResult:
    complementary_fit_score: float
    supplementary_fit_index: float
    gap_coverage: float | None
    balance_gain: float | None
    redundancy: float | None
    verdict: str
    simulated_scores: dict[str, float]
    score_deltas: dict[str, float]
    gaps_filled: list[str]
    gaps_missed: list[str]
    overlaps: list[str]
    risk_flags: list[str] = field(default_factory=list)
    insights: list[DimensionInsight] = field(default_factory=list)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class ProfileNorms:
    """Centro e dispersão do perfil de um time — a régua contra a qual as
    dimensões daquele time são classificadas."""

    center: float
    spread: float

    @property
    def is_uniform(self) -> bool:
        """Time igualmente forte (ou fraco) em tudo: não há o que priorizar."""
        return self.spread < MIN_MEANINGFUL_SPREAD


def profile_norms(team_scores: dict[str, float]) -> ProfileNorms:
    values = [v for v in team_scores.values()]
    if not values:
        return ProfileNorms(center=0.0, spread=0.0)
    center = sum(values) / len(values)
    spread = pstdev(values) if len(values) > 1 else 0.0
    return ProfileNorms(center=center, spread=spread)


def classify_dimension(team_score: float, norms: ProfileNorms | None = None) -> str:
    """Classifica uma dimensão **contra o próprio perfil do time**.

    A classificação é relativa, não absoluta, porque o instrumento é de escolha
    forçada: privilegiar uma conduta implica não privilegiar as outras, e a
    pontuação é ancorada no nível de acaso (3.0 = frequência que o acaso
    produziria). Duas consequências tornam limiares fixos inúteis aqui:

    * A média de um time diverso regride ao centro por construção — com corte
      absoluto em 3.5, *toda* dimensão de *todo* time equilibrado viraria lacuna
      e nenhuma seria força.
    * Não existe "nota boa" absoluta num escore normativo: 4.0 significa "escolhe
      esta conduta bem mais que o acaso", não "domina a competência".

    Comparar cada dimensão com o centro do próprio time é o que a expressão
    "lacuna do time" quer dizer: onde este time é comparativamente mais fraco.

    `norms=None` mantém a assinatura antiga usável para um perfil isolado, caso
    em que nada pode ser classificado por falta de referência.
    """
    if norms is None or norms.is_uniform:
        return DimensionStatus.ADEQUATE
    if team_score < norms.center - RELATIVE_BAND * norms.spread:
        return DimensionStatus.GAP
    if team_score > norms.center + RELATIVE_BAND * norms.spread:
        return DimensionStatus.STRENGTH
    return DimensionStatus.ADEQUATE


def deficit_weight(team_score: float, norms: ProfileNorms | None = None) -> float:
    """0.0 (no centro ou acima) a 1.0 (o ponto mais fraco do time).

    É o peso que a dimensão recebe no perfil-alvo da vaga.
    """
    if norms is None or norms.is_uniform:
        return 0.0
    return _clamp((norms.center - team_score) / (2 * norms.spread))


def simulate_team_average(team_score: float, candidate_score: float, team_size: int) -> float:
    """Média do time depois da contratação: (média × N + nota do candidato) / (N + 1)."""
    if team_size <= 0:
        return candidate_score
    return ((team_score * team_size) + candidate_score) / (team_size + 1)


def _spread(scores: list[float]) -> float:
    if len(scores) < 2:
        return 0.0
    return max(scores) - min(scores)


def _simulate_profile(
    team_scores: dict[str, float], candidate_scores: dict[str, float], dimensions: list[str], team_size: int
) -> dict[str, float]:
    return {
        dim: simulate_team_average(team_scores.get(dim, 0.0), candidate_scores.get(dim, 0.0), team_size)
        for dim in dimensions
    }


def _ideal_candidate(team_scores: dict[str, float], dimensions: list[str], norms: ProfileNorms) -> dict[str, float]:
    """Candidato teórico que maximiza o equilíbrio: nota máxima onde o time está
    abaixo do próprio centro, apenas acompanha o time no resto."""
    return {
        dim: SCALE_MAX if team_scores.get(dim, 0.0) < norms.center else team_scores.get(dim, 0.0) for dim in dimensions
    }


def _balance_gain(
    team_scores: dict[str, float],
    candidate_scores: dict[str, float],
    dimensions: list[str],
    team_size: int,
    norms: ProfileNorms,
) -> float | None:
    """Ganho de equilíbrio do perfil do time, normalizado pelo melhor ganho possível.

    Retorna 0.0–1.0, ou None quando não há desequilíbrio a corrigir. Normalizar
    pelo candidato ideal remove a dependência do tamanho do time: adicionar uma
    pessoa a um time de 12 muda pouco a média, mas o quociente continua
    comparável entre candidatos da mesma vaga.
    """
    current = [team_scores.get(d, 0.0) for d in dimensions]
    spread_before = _spread(current)
    if spread_before <= 0:
        return None

    actual_after = _spread(list(_simulate_profile(team_scores, candidate_scores, dimensions, team_size).values()))
    ideal = _ideal_candidate(team_scores, dimensions, norms)
    ideal_after = _spread(list(_simulate_profile(team_scores, ideal, dimensions, team_size).values()))

    max_reduction = spread_before - ideal_after
    if max_reduction <= 1e-9:
        return None

    return _clamp((spread_before - actual_after) / max_reduction)


def _gap_coverage(
    team_scores: dict[str, float], candidate_scores: dict[str, float], dimensions: list[str], norms: ProfileNorms
) -> float | None:
    """Quanto das lacunas do time o candidato cobre, ponderado pelo tamanho de cada lacuna."""
    weighted_total = 0.0
    weight_sum = 0.0

    for dim in dimensions:
        team = team_scores.get(dim, 0.0)
        weight = deficit_weight(team, norms)
        if weight <= 0:
            continue

        headroom = SCALE_MAX - team
        lift = _clamp((candidate_scores.get(dim, 0.0) - team) / headroom) if headroom > 0 else 0.0

        weighted_total += weight * lift
        weight_sum += weight

    if weight_sum <= 0:
        return None
    return weighted_total / weight_sum


def _redundancy(
    team_scores: dict[str, float], candidate_scores: dict[str, float], dimensions: list[str], norms: ProfileNorms
) -> float | None:
    """Fit suplementar: quanto da força do candidato apenas duplica força que o time já tem.

    A duplicação de cada dimensão é medida **contra a força que o time já tem
    ali**: 1.0 significa que o candidato traz tanto daquela competência quanto o
    time já tinha, 0.0 que ele fica no nível médio do time. Normalizar contra a
    escala ou contra a dispersão tornaria o valor máximo dependente do perfil, e
    o limiar de "suplementar em excesso" ficaria inalcançável em uns times e
    trivial em outros.

    Ponderado por quão forte o time já é na dimensão — reforçar algo que o time
    faz bem custa mais em redundância do que reforçar algo mediano.
    """
    if norms.is_uniform:
        return None

    weighted_total = 0.0
    weight_sum = 0.0

    for dim in dimensions:
        team = team_scores.get(dim, 0.0)
        if classify_dimension(team, norms) != DimensionStatus.STRENGTH:
            continue

        headroom = team - norms.center
        if headroom <= 1e-9:
            continue

        weight = _clamp(headroom / (2 * norms.spread))
        duplication = _clamp((candidate_scores.get(dim, 0.0) - norms.center) / headroom)

        weighted_total += weight * duplication
        weight_sum += weight

    if weight_sum <= 0:
        return None
    return weighted_total / weight_sum


def _supplementary_index(
    team_scores: dict[str, float], candidate_scores: dict[str, float], dimensions: list[str]
) -> float:
    """0–100. Quão parecido o candidato é com o time (100 = perfil idêntico)."""
    if not dimensions:
        return 0.0
    span = SCALE_MAX - SCALE_MIN
    distance = sum(abs(candidate_scores.get(d, 0.0) - team_scores.get(d, 0.0)) for d in dimensions) / len(dimensions)
    return round(100.0 * _clamp(1.0 - (distance / span)), 1)


def _explain(dim: str, team: float, candidate: float, status: str, norms: ProfileNorms) -> tuple[str, str]:
    if status == DimensionStatus.GAP:
        if candidate < MIN_CANDIDATE_FLOOR:
            return (
                "AGGRAVATES_GAP",
                f"{dim} já é lacuna do time ({team:.1f}) e o candidato também pontua baixo "
                f"({candidate:.1f}) — a contratação aprofunda o buraco.",
            )
        # Só conta como lacuna coberta se o candidato traz a dimensão pelo menos
        # ao centro do perfil do time. Pontuar acima de um time fraco, mas ainda
        # abaixo do centro, não fecha a lacuna — rotular isso como "coberta"
        # enganaria o recrutador.
        if candidate >= norms.center:
            return (
                "FILLS_GAP",
                f"{dim} é lacuna do time ({team:.1f}) e o candidato pontua {candidate:.1f} — cobre a lacuna.",
            )
        if candidate > team:
            return (
                "PARTIAL_LIFT",
                f"{dim} é lacuna do time ({team:.1f}) e o candidato ({candidate:.1f}) melhora a "
                f"média, mas continua abaixo do nível médio do time ({norms.center:.1f}) — "
                f"a lacuna segue aberta.",
            )
        return (
            "NEUTRAL",
            f"{dim} é lacuna do time ({team:.1f}) e o candidato não a supera ({candidate:.1f}).",
        )

    if status == DimensionStatus.STRENGTH:
        if classify_dimension(candidate, norms) == DimensionStatus.STRENGTH:
            return (
                "REDUNDANT",
                f"{dim} já é força do time ({team:.1f}) e o candidato repete o mesmo perfil "
                f"({candidate:.1f}) — reforço sem ganho de composição.",
            )
        if candidate < MIN_CANDIDATE_FLOOR:
            return (
                "DILUTES_STRENGTH",
                f"{dim} é força do time ({team:.1f}), mas o candidato pontua {candidate:.1f} e "
                f"puxa a média para baixo.",
            )
        return ("NEUTRAL", f"{dim} é força do time ({team:.1f}); o candidato ({candidate:.1f}) não altera isso.")

    return (
        "NEUTRAL",
        f"{dim} está em nível adequado no time ({team:.1f}); o candidato pontua {candidate:.1f}.",
    )


def evaluate_fit(
    team_scores: dict[str, float],
    candidate_scores: dict[str, float],
    team_size: int,
    respondent_count: int,
    dimensions: list[str] | None = None,
) -> FitResult:
    """Calcula o fit complementar do candidato contra o perfil agregado do time.

    Args:
        team_scores: média do time por dimensão.
        candidate_scores: notas do candidato por dimensão.
        team_size: nº de integrantes usado na simulação pós-contratação.
        respondent_count: nº de integrantes que efetivamente responderam o teste.
        dimensions: dimensões a considerar. Padrão: união das chaves recebidas.
    """
    dims = sorted(dimensions) if dimensions else sorted(set(team_scores) | set(candidate_scores))
    # A régua do time é calculada uma vez e usada em toda a avaliação.
    norms = profile_norms({d: team_scores[d] for d in dims if d in team_scores})

    simulated = {d: round(v, 2) for d, v in _simulate_profile(team_scores, candidate_scores, dims, team_size).items()}
    deltas = {d: round(simulated[d] - team_scores.get(d, 0.0), 2) for d in dims}

    gaps_filled: list[str] = []
    gaps_missed: list[str] = []
    overlaps: list[str] = []
    risk_flags: list[str] = []
    insights: list[DimensionInsight] = []

    for dim in dims:
        team = team_scores.get(dim, 0.0)
        candidate = candidate_scores.get(dim, 0.0)
        status = classify_dimension(team, norms)
        contribution, explanation = _explain(dim, team, candidate, status, norms)

        if contribution == "FILLS_GAP":
            gaps_filled.append(dim)
        elif status == DimensionStatus.GAP:
            # PARTIAL_LIFT entra aqui: a média sobe, mas a lacuna sobrevive à contratação.
            gaps_missed.append(dim)
        elif contribution == "REDUNDANT":
            overlaps.append(dim)

        if candidate < MIN_CANDIDATE_FLOOR and candidate_scores:
            if team < MIN_CANDIDATE_FLOOR:
                risk_flags.append(
                    f"{dim} fica descoberta: nem o time ({team:.1f}) nem o candidato "
                    f"({candidate:.1f}) atingem o piso mínimo de {MIN_CANDIDATE_FLOOR}."
                )
            else:
                risk_flags.append(
                    f"Candidato abaixo do piso mínimo ({MIN_CANDIDATE_FLOOR}) em {dim}: "
                    f"{candidate:.1f} — o time cobre ({team:.1f}), mas a média cai."
                )

        insights.append(
            DimensionInsight(
                dimension=dim,
                team_score=round(team, 2),
                candidate_score=round(candidate, 2),
                simulated_score=simulated[dim],
                delta=deltas[dim],
                status=status,
                contribution=contribution,
                explanation=explanation,
            )
        )

    coverage = _gap_coverage(team_scores, candidate_scores, dims, norms)
    balance = _balance_gain(team_scores, candidate_scores, dims, team_size, norms)
    redundancy = _redundancy(team_scores, candidate_scores, dims, norms)

    components = [
        (coverage, WEIGHT_GAP_COVERAGE),
        (balance, WEIGHT_BALANCE_GAIN),
        (None if redundancy is None else 1.0 - redundancy, WEIGHT_NON_REDUNDANCY),
    ]
    available = [(v, w) for v, w in components if v is not None]

    if available:
        total_weight = sum(w for _, w in available)
        score = 100.0 * sum(v * w for v, w in available) / total_weight
    else:
        # Time sem lacuna, sem desequilíbrio e sem força consolidada: não há
        # composição a otimizar. Cai para a força absoluta do candidato.
        mean_candidate = sum(candidate_scores.values()) / len(candidate_scores) if candidate_scores else 0.0
        score = 100.0 * _clamp((mean_candidate - SCALE_MIN) / (SCALE_MAX - SCALE_MIN))

    # Violação crítica: a competência está **ausente** no time, o candidato
    # também não a tem, e a contratação a deixa como encontrou.
    #
    # As três condições juntas importam. "Candidato abaixo do piso" sozinho não
    # serve porque o instrumento é de escolha forçada: privilegiar uma conduta
    # implica não privilegiar as outras, então todo respondente fica baixo em
    # alguma dimensão — punir isso reprovaria todo mundo e esvaziaria o veredito.
    # E exigir que o time também esteja abaixo do piso não basta: um candidato
    # que puxa a dimensão para cima, ainda que sem atingir o piso, está ajudando,
    # não agravando.
    critical_violations = [
        d
        for d in dims
        if candidate_scores.get(d, 0.0) < MIN_CANDIDATE_FLOOR
        and team_scores.get(d, 0.0) < MIN_CANDIDATE_FLOOR
        and candidate_scores.get(d, 0.0) <= team_scores.get(d, 0.0)
    ]
    if critical_violations:
        score = min(score, CRITICAL_VIOLATION_CAP)

    verdict = _verdict(
        coverage=coverage,
        redundancy=redundancy,
        respondent_count=respondent_count,
        critical_violations=critical_violations,
    )

    if verdict == FitVerdict.INSUFFICIENT_TEAM_DATA:
        risk_flags.insert(
            0,
            "Nenhum integrante do time respondeu ao diagnóstico — o fit foi calculado "
            "apenas sobre a força absoluta do candidato e não representa complementaridade.",
        )
    if verdict == FitVerdict.EXCESSIVE_SUPPLEMENTARY:
        risk_flags.insert(
            0,
            "Fit suplementar em excesso: o candidato reforça o que o time já faz bem e deixa as lacunas descobertas.",
        )

    return FitResult(
        complementary_fit_score=round(score, 1),
        supplementary_fit_index=_supplementary_index(team_scores, candidate_scores, dims),
        gap_coverage=None if coverage is None else round(coverage, 3),
        balance_gain=None if balance is None else round(balance, 3),
        redundancy=None if redundancy is None else round(redundancy, 3),
        verdict=verdict,
        simulated_scores=simulated,
        score_deltas=deltas,
        gaps_filled=gaps_filled,
        gaps_missed=gaps_missed,
        overlaps=overlaps,
        risk_flags=risk_flags,
        insights=insights,
    )


def _verdict(
    coverage: float | None,
    redundancy: float | None,
    respondent_count: int,
    critical_violations: list[str],
) -> str:
    if respondent_count <= 0:
        return FitVerdict.INSUFFICIENT_TEAM_DATA
    if critical_violations:
        return FitVerdict.BELOW_MINIMUM
    if redundancy is not None and redundancy >= EXCESSIVE_REDUNDANCY and (coverage or 0.0) <= LOW_GAP_COVERAGE:
        return FitVerdict.EXCESSIVE_SUPPLEMENTARY
    if coverage is not None and coverage >= 0.6:
        return FitVerdict.COMPLEMENTARY
    return FitVerdict.BALANCED


def team_profile_dispersion(team_scores: dict[str, float]) -> float:
    """Desvio-padrão populacional do perfil do time. Alto = time especializado
    e desbalanceado; baixo = time uniforme."""
    values = list(team_scores.values())
    if len(values) < 2:
        return 0.0
    return round(pstdev(values), 3)
