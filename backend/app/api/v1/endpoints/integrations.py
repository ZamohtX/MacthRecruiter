"""Endpoints da integração com o OxeTech Academy.

Expõem, dentro da própria API do produto, o pool de talentos do Academy: o
recrutador autenticado consulta os agregados do programa e a lista de alunos
disponíveis sem sair do MatchRecruiter. É a API pública sendo consumida e usada
em tempo real — não só num script.

Somente leitura e sob autenticação, coerente com o resto do produto. Falhas da
API externa viram 502 (culpa do upstream), não 500.
"""

import random

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_recruiter, get_current_user
from app.db.session import get_db
from app.integrations.academy.client import AcademyAPIError, AcademyClient
from app.integrations.academy.roster import synthetic_talent_pool
from app.integrations.academy.schemas import AcademyAluno, AcademyStats
from app.integrations.academy.simulator import AcademyMatchSimulator, SimulationResult
from app.models.team import Team
from app.models.user import User
from app.repositories.job_repository import JobRepository
from app.repositories.questionnaire_repository import QuestionnaireRepository
from app.repositories.team_repository import TeamRepository
from app.schemas.integration import (
    SimulatedCandidate,
    SimulateTeamRequest,
    SimulateTeamResponse,
)
from app.services.fit_engine import team_profile_dispersion
from app.services.recruitment_service import RecruitmentService
from app.services.soft_skills_service import SoftSkillsService

router = APIRouter()

# Semente aleatória máxima (32 bits) para o sorteio do time quando o cliente não
# fixa uma — cada chamada monta um time diferente.
_MAX_SEED = 2**32 - 1


def _upstream_error(exc: AcademyAPIError) -> HTTPException:
    # 401 do Academy é problema de configuração nossa (token), não do cliente
    # que chamou nosso endpoint — reportamos como 502 com a causa.
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@router.get("/academy/ping")
async def academy_ping(_: User = Depends(get_current_user)) -> dict:
    """Testa a conexão e o token com a API do Academy."""
    try:
        async with AcademyClient.from_settings() as academy:
            return await academy.ping()
    except AcademyAPIError as exc:
        raise _upstream_error(exc)


@router.get("/academy/stats", response_model=AcademyStats)
async def academy_stats(_: User = Depends(get_current_user)) -> AcademyStats:
    """Agregados do programa: empresas ativas e alunos habilitados/disponíveis."""
    try:
        async with AcademyClient.from_settings() as academy:
            return await academy.stats()
    except AcademyAPIError as exc:
        raise _upstream_error(exc)


@router.get("/academy/talent-pool", response_model=list[AcademyAluno])
async def academy_talent_pool(
    tecnologia: str | None = Query(None, description="Filtra por tecnologia declarada."),
    modalidade: str | None = Query(None),
    turno: str | None = Query(None),
    disponivel: bool | None = Query(True, description="Só alunos disponíveis por padrão."),
    limit: int = Query(50, ge=1, le=100),
    _: User = Depends(get_current_user),
) -> list[AcademyAluno]:
    """Pool de talentos: alunos habilitados do Academy, já normalizados."""
    try:
        async with AcademyClient.from_settings() as academy:
            return await academy.list_alunos_all(
                max_items=limit,
                tecnologia=tecnologia,
                modalidade=modalidade,
                turno=turno,
                disponivel=disponivel,
            )
    except AcademyAPIError as exc:
        raise _upstream_error(exc)


async def _load_talent_pool(limit: int) -> tuple[list[AcademyAluno], str]:
    """Alunos para a geração: API real quando há alunos, senão roster sintético.

    A API vazia (turma entre ciclos) e a API indisponível **não** são erro aqui —
    o produto tem que gerar um time de qualquer jeito. Só nesses casos caímos para
    o roster sintético, sinalizando a origem em `source` para a interface ser honesta.
    """
    try:
        async with AcademyClient.from_settings() as academy:
            alunos = await academy.list_alunos_all(max_items=limit, disponivel=True)
        if alunos:
            return alunos, "academy_api"
    except AcademyAPIError:
        pass  # rede/auth/rate-limit — segue com o sintético
    return synthetic_talent_pool(), "synthetic"


def _to_response(result: SimulationResult) -> SimulateTeamResponse:
    return SimulateTeamResponse(
        source=result.source,
        team_id=result.team_id,
        team_name=result.team_name,
        team_scores=result.team_scores,
        job_id=result.job_id,
        job_title=result.job_title,
        respondent_count=result.respondent_count,
        dispersion_before=result.dispersion_before,
        candidates=[
            SimulatedCandidate(
                candidate_id=candidate.candidate_id,
                aluno_id=candidate.aluno_id,
                name=candidate.name,
                techs=candidate.techs,
                candidate_scores=candidate.candidate_scores,
                fit_score=candidate.fit_score,
                supplementary_fit_index=candidate.supplementary_fit_index,
                verdict=candidate.verdict,
                gaps_filled=candidate.gaps_filled,
                gaps_missed=candidate.gaps_missed,
            )
            for candidate in result.ranked
        ],
    )


async def _find_existing_team(db: AsyncSession, owner_id, team_name: str) -> Team | None:
    """Turma mais recente com este nome que o recrutador já gerou.

    Base da idempotência: reabrir a aba não deve empilhar uma turma nova a cada
    vez. Só considera turmas com integrantes — uma casca sem gente seria
    reconstruída vazia.
    """
    teams = await TeamRepository(db).list_teams_for_user(owner_id)
    matches = [t for t in teams if t.owner_id == owner_id and t.name == team_name]
    matches.sort(key=lambda t: t.created_at, reverse=True)
    for team in matches:
        members = await TeamRepository(db).get_team_members(team.id)
        if members:
            return team
    return None


async def _reconstruct_from_team(db: AsyncSession, team: Team, questionnaire_id) -> SimulateTeamResponse | None:
    """Monta a resposta a partir de uma turma já persistida, sem recriar nada.

    Reaproveita o mesmo ranking do painel de vagas (`get_job_candidates`), então
    a turma reaberta mostra exatamente o que a tela da vaga mostraria.
    """
    jobs = await JobRepository(db).list_jobs_for_teams([team.id])
    if not jobs:
        return None
    job = jobs[0]

    profile = await SoftSkillsService(db).load_team_profile(team.id, questionnaire_id)
    summaries = await RecruitmentService(db).get_job_candidates(job.id)

    return SimulateTeamResponse(
        source="synthetic",
        team_id=team.id,
        team_name=team.name,
        team_scores=profile.dimension_scores,
        job_id=job.id,
        job_title=job.title,
        respondent_count=profile.respondent_count,
        dispersion_before=team_profile_dispersion(profile.dimension_scores),
        candidates=[
            SimulatedCandidate(
                candidate_id=summary.candidate_id,
                name=summary.candidate_name,
                candidate_scores=summary.candidate_scores or {},
                fit_score=summary.fit_score or 0.0,
                supplementary_fit_index=summary.supplementary_fit_index or 0.0,
                verdict=summary.verdict or "INSUFFICIENT_TEAM_DATA",
                gaps_filled=summary.gaps_filled,
            )
            for summary in summaries
        ],
    )


@router.post("/academy/simulate", response_model=SimulateTeamResponse)
async def academy_simulate(
    payload: SimulateTeamRequest | None = None,
    current_user: User = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_db),
) -> SimulateTeamResponse:
    """Monta um time aleatório com os alunos do Academy e ranqueia candidatos.

    Importa os alunos como usuários, sorteia time + pool de candidatos, aplica o
    diagnóstico comportamental em todos e devolve o time e os candidatos já
    ranqueados por fit complementar. O time e a vaga são persistidos em nome do
    recrutador logado, então aparecem nas telas normais de Times/Vagas/Simulação.
    """
    params = payload or SimulateTeamRequest()

    questionnaire = await QuestionnaireRepository(db).get_default()
    if questionnaire is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum questionário padrão configurado. Rode o seed do instrumento antes de gerar um time.",
        )

    # Idempotência: por padrão, reabrir a aba reaproveita a turma já gerada em vez
    # de criar outra. "Gerar outro time" (regenerate=True) pula isto e sorteia nova.
    if not params.regenerate:
        existing = await _find_existing_team(db, current_user.id, params.team_name)
        if existing is not None:
            reconstructed = await _reconstruct_from_team(db, existing, questionnaire.id)
            if reconstructed is not None:
                return reconstructed

    alunos, source = await _load_talent_pool(params.limit)
    if len(alunos) < params.team_size + 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Pool insuficiente: {len(alunos)} aluno(s) para um time de "
                f"{params.team_size} mais ao menos 1 candidato."
            ),
        )

    seed = params.seed if params.seed is not None else random.randint(0, _MAX_SEED)
    result = await AcademyMatchSimulator(db, questionnaire).run(
        alunos,
        team_size=params.team_size,
        team_name=params.team_name,
        job_title=params.job_title,
        source=source,
        seed=seed,
        owner=current_user,
    )
    return _to_response(result)
