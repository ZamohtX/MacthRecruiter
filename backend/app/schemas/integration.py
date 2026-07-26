"""Schemas da geração de time a partir do pool de talentos do OxeTech Academy.

O endpoint `POST /integrations/academy/simulate` monta um time aleatório com os
alunos do Academy (ou o roster sintético, quando a API está entre turmas), aplica
o diagnóstico comportamental em todos e devolve o time e os candidatos já
ranqueados pelo fit complementar. `candidate_id`, `team_id` e `job_id` são os ids
reais persistidos — a interface usa-os para navegar às telas de vaga/simulação.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class SimulateTeamRequest(BaseModel):
    """Parâmetros da geração. Tudo tem default: um POST vazio já funciona."""

    team_size: int = Field(6, ge=2, le=20, description="Quantos alunos formam o time.")
    team_name: str = "Squad OxeTech"
    job_title: str = "Pessoa Desenvolvedora — vaga complementar"
    # Vazio → semente aleatória por chamada, para cada geração sortear um time
    # diferente ("time aleatório"). Informar um valor torna a geração reprodutível.
    seed: int | None = None
    limit: int = Field(24, ge=3, le=100, description="Máx. de alunos puxados do pool.")
    # Por padrão a geração é idempotente: se o recrutador já tem uma turma com
    # este nome, ela é reaproveitada em vez de criar outra. `regenerate=True`
    # força um time novo (o botão "Gerar outro time").
    regenerate: bool = False


class SimulatedCandidate(BaseModel):
    """Um candidato do pool, já com perfil medido e fit calculado."""

    candidate_id: UUID
    # Ausente quando a turma é reconstruída do banco (o vínculo com o id do
    # aluno do Academy não é persistido por candidato).
    aluno_id: int | None = None
    name: str
    techs: list[str] = Field(default_factory=list)
    # As 10 soft skills do candidato (1–5). É o que alimenta o radar isolado e,
    # sobreposto a `team_scores`, o radar combinado.
    candidate_scores: dict[str, float]
    fit_score: float
    supplementary_fit_index: float
    verdict: str
    gaps_filled: list[str] = Field(default_factory=list)
    gaps_missed: list[str] = Field(default_factory=list)


class AiSummaryResponse(BaseModel):
    """Resumo do candidato em linguagem simples."""

    summary: str
    # "ai" quando veio do Gemini; "fallback" quando caiu no texto-regra.
    source: str
    model: str | None = None


class SimulateTeamResponse(BaseModel):
    source: str  # "academy_api" | "synthetic"
    team_id: UUID
    team_name: str
    # Média das 10 soft skills do time — a "forma" do time no radar.
    team_scores: dict[str, float]
    job_id: UUID
    job_title: str
    respondent_count: int
    dispersion_before: float
    candidates: list[SimulatedCandidate] = Field(default_factory=list)
