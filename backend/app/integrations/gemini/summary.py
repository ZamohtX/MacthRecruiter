"""Resumo do candidato: prompt para o Gemini e um fallback determinístico.

O resumo traduz a análise de fit (números, lacunas, veredito) em duas ou três
frases de linguagem simples — é a "conclusão" que abre a tela do candidato. O
fallback existe para quando o Gemini está fora (sem chave, quota, rede): usa os
mesmos dados, então a tela nunca fica sem um resumo.
"""

from app.schemas.job import ImpactAnalysisResponse

_VERDICT_PT = {
    "COMPLEMENTARY": "complementar ao time (cobre lacunas)",
    "BALANCED": "equilibrado em relação ao time",
    "EXCESSIVE_SUPPLEMENTARY": "muito parecido com o time (reforça o que já é forte)",
    "BELOW_MINIMUM": "abaixo do mínimo em competências que o time precisa",
    "INSUFFICIENT_TEAM_DATA": "sem diagnóstico suficiente do time para comparar",
}


def _top_dims(scores: dict[str, float], n: int = 3, *, highest: bool = True) -> list[str]:
    items = sorted(scores.items(), key=lambda kv: kv[1], reverse=highest)
    return [dim for dim, _ in items[:n]]


def build_prompt(impact: ImpactAnalysisResponse) -> str:
    """Monta o prompt em português, ancorado só nos dados da análise."""
    sim = impact.simulation
    forcas = ", ".join(_top_dims(impact.candidate_scores)) or "—"
    fracas = ", ".join(_top_dims(impact.candidate_scores, highest=False)) or "—"
    cobre = ", ".join(sim.gaps_filled) or "nenhuma lacuna clara"
    descobre = ", ".join(sim.gaps_missed) or "nenhuma"
    dilui = ", ".join(sim.overlaps) or "nenhuma"

    return (
        "Você é um assistente de RH. Escreva um resumo curto (2 a 3 frases, no máximo "
        "70 palavras), em português do Brasil, linguagem simples e direta, sobre o "
        "encaixe deste candidato no time. Sem títulos, sem bullet points, sem repetir "
        "os números crus — interprete-os. Termine com uma orientação prática (avançar, "
        "avaliar com cuidado, ou provavelmente não). Deixe implícito que é apoio à "
        "decisão, não um veredito definitivo.\n\n"
        f"Candidato: {impact.candidate_name}\n"
        f"Fit complementar (0–100, quanto cobre as lacunas do time): {impact.fit_score:.0f}\n"
        f"Semelhança com o time (0–100): {impact.supplementary_fit_index:.0f}\n"
        f"Veredito do sistema: {_VERDICT_PT.get(impact.verdict, impact.verdict)}\n"
        f"Competências mais fortes do candidato: {forcas}\n"
        f"Competências mais fracas do candidato: {fracas}\n"
        f"Lacunas do time que ele cobre: {cobre}\n"
        f"Lacunas que continuam descobertas: {descobre}\n"
        f"Competências onde ele só reforça o que o time já tem: {dilui}\n"
    )


def fallback_summary(impact: ImpactAnalysisResponse) -> str:
    """Resumo-regra quando o Gemini está indisponível — mesmos dados, sem IA."""
    sim = impact.simulation
    cobre = sim.gaps_filled
    veredito = _VERDICT_PT.get(impact.verdict, impact.verdict)

    frase_cobre = (
        f"Cobre lacunas do time em {', '.join(cobre)}." if cobre else "Não cobre lacunas claras do time."
    )
    if impact.fit_score >= 60:
        orientacao = "Vale avançar na avaliação."
    elif impact.fit_score >= 35:
        orientacao = "Avalie com cuidado o que ele agrega além do que o time já tem."
    else:
        orientacao = "Provavelmente adiciona mais do mesmo do que o time precisa."

    return (
        f"{impact.candidate_name} tem fit complementar de {impact.fit_score:.0f} e é {veredito}. "
        f"{frase_cobre} {orientacao}"
    )
