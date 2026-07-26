"""Demo ponta a ponta: OxeTech Academy → MatchRecruiter.

Consome a API pública de Desenvolvedores do Academy, monta uma equipe aleatória
com os alunos, aplica o diagnóstico comportamental em todos e percorre os
candidatos ranqueando quem melhor se encaixa no time pelo fit complementar.

    python -m scripts.academy_match_demo
    python -m scripts.academy_match_demo --team-size 5 --limit 30 --seed 7

Quando a API não devolve alunos (o programa pode estar entre turmas — foi o caso
em 26/07/2026), a demo cai para um roster sintético determinístico e diz isso na
saída. O token vem de ACADEMY_API_TOKEN no .env; sem token, só o roster sintético.
"""

import argparse
import asyncio
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# O console do Windows sobe em cp1252 e não engole as barras de caixa nem as
# setas do relatório. Forçar UTF-8 evita UnicodeEncodeError na impressão.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Banco descartável só para a demo — criado antes de importar o app, como o
# dev_local faz, para o settings já subir apontando pro SQLite.
_DB_PATH = Path(tempfile.gettempdir()) / "academy_match_demo.db"
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_DB_PATH.as_posix()}")

from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

import app.models  # noqa: E402, F401  — registra os modelos no metadata
from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.seed import seed_default_questionnaire  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.integrations.academy.client import AcademyAPIError, AcademyClient  # noqa: E402
from app.integrations.academy.roster import synthetic_talent_pool  # noqa: E402
from app.integrations.academy.schemas import AcademyAluno  # noqa: E402
from app.integrations.academy.simulator import AcademyMatchSimulator, SimulationResult  # noqa: E402

BAR = "─" * 72


def _print_header(title: str) -> None:
    print(f"\n{BAR}\n {title}\n{BAR}")


async def _load_pool(limit: int) -> tuple[list[AcademyAluno], str]:
    """Tenta a API real; cai para o roster sintético se vier vazia ou falhar."""
    if not settings.ACADEMY_API_TOKEN:
        print("⚠  ACADEMY_API_TOKEN não configurado — usando roster sintético.")
        return synthetic_talent_pool(), "synthetic"

    try:
        async with AcademyClient.from_settings() as academy:
            ping = await academy.ping()
            who = ping.get("aluno", {}).get("nome", "?") if isinstance(ping, dict) else "?"
            print(f"✓ Conectado à API do Academy (token de: {who.strip()}).")

            stats = await academy.stats()
            print(
                f"  Programa agora: {stats.empresas_ativas} empresas ativas · "
                f"{stats.alunos_habilitados} alunos habilitados · "
                f"{stats.alunos_disponiveis} disponíveis."
            )

            alunos = await academy.list_alunos_all(max_items=limit, disponivel=True)
    except AcademyAPIError as exc:
        print(f"⚠  API do Academy indisponível ({exc}) — usando roster sintético.")
        return synthetic_talent_pool(), "synthetic"

    if not alunos:
        print("⚠  API respondeu, mas 0 alunos disponíveis no momento — usando roster sintético.")
        return synthetic_talent_pool(), "synthetic"

    print(f"✓ {len(alunos)} aluno(s) reais carregados da API.")
    return alunos, "academy_api"


def _print_result(result: SimulationResult) -> None:
    origem = "API do Academy" if result.source == "academy_api" else "roster sintético (API sem alunos)"

    _print_header(f"TIME: {result.team_name}  ·  origem: {origem}")
    print(f" Integrantes ({result.respondent_count} responderam o diagnóstico):")
    for name in result.team_members:
        print(f"   • {name}")
    print(f"\n Perfil de soft skills do time (radar) — dispersão {result.dispersion_before:.3f}")
    print(" (dispersão alta = radar irregular, com lacunas a cobrir)")
    for dim, score in sorted(result.team_scores.items(), key=lambda kv: -kv[1]):
        bar = "█" * round(score * 6)
        print(f"   {dim:<26} {score:>4.2f}  {bar}")

    _print_header(f"CANDIDATOS RANQUEADOS  ·  vaga: {result.job_title}")
    print(f" {'#':>2}  {'fit':>5}  {'radar→':>7}  {'veredito':<24} candidato")
    print(f" {'':>2}  {'':>5}  {'':>7}  {'':<24} (lacunas que cobre)")
    print(f" {'-'*2}  {'-'*5}  {'-'*7}  {'-'*24} {'-'*30}")
    for pos, cand in enumerate(result.ranked, start=1):
        seta = "▼" if cand.dispersion_after < result.dispersion_before else "▲"
        cobre = ", ".join(cand.gaps_filled) if cand.gaps_filled else "—"
        print(
            f" {pos:>2}  {cand.fit_score:>5.1f}  {cand.dispersion_after:>5.3f}{seta}  "
            f"{cand.verdict:<24} {cand.name}"
        )
        print(f" {'':>2}  {'':>5}  {'':>7}  {'':<24} cobre: {cobre}  ·  stack: {', '.join(cand.techs) or '—'}")

    best = result.best
    if best:
        delta = result.dispersion_before - best.dispersion_after
        _print_header("MELHOR ENCAIXE")
        print(f" {best.name}  —  fit {best.fit_score:.1f}  ({best.verdict})")
        print(f" Stack: {', '.join(best.techs) or '—'}")
        print(f" Lacunas cobertas: {', '.join(best.gaps_filled) or 'nenhuma'}")
        print(
            f" Efeito no radar do time: dispersão {result.dispersion_before:.3f} → "
            f"{best.dispersion_after:.3f}  ({'−' if delta >= 0 else '+'}{abs(delta):.3f}) "
            f"— {'radar mais regular ✓' if delta >= 0 else 'radar menos regular'}"
        )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Demo Academy → MatchRecruiter")
    parser.add_argument("--team-size", type=int, default=6, help="Integrantes do time (padrão: 6).")
    parser.add_argument("--limit", type=int, default=None, help="Máx. de alunos a puxar da API.")
    parser.add_argument("--seed", type=int, default=42, help="Semente do sorteio do time.")
    args = parser.parse_args()

    limit = args.limit or settings.ACADEMY_MAX_ALUNOS

    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()

    _print_header("OXETECH ACADEMY  →  MATCHRECRUITER")
    pool, source = await _load_pool(limit)

    if len(pool) < args.team_size + 1:
        print(f"\nPool insuficiente ({len(pool)}) para um time de {args.team_size} + candidatos.")
        raise SystemExit(1)

    async with AsyncSessionLocal() as session:
        questionnaire = await seed_default_questionnaire(session)
        simulator = AcademyMatchSimulator(session, questionnaire)
        result = await simulator.run(pool, team_size=args.team_size, source=source, seed=args.seed)

    _print_result(result)
    print()


if __name__ == "__main__":
    asyncio.run(main())
