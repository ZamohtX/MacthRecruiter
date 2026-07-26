"""Prepara um banco local em SQLite, sem Docker e sem PostgreSQL.

Cria o schema a partir dos modelos e aplica o seed do instrumento padrão. Serve
para desenvolver e demonstrar a aplicação em uma máquina onde o daemon do Docker
não está no ar.

⚠️ **Isto não substitui as migrações.** O schema é criado direto de
`Base.metadata`, contornando o Alembic — o que significa que uma migração
quebrada não seria percebida por aqui. PostgreSQL + `alembic upgrade head`
continua sendo o caminho de produção e o que o CI deve exercitar.

Uso:
    make dev-local          # cria o banco e sobe a API
    python -m scripts.dev_local
"""

import asyncio
import os
import sys
from pathlib import Path

# Permite rodar como script solto (`python scripts/dev_local.py`).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_SQLITE_URL = "sqlite+aiosqlite:///./matchrecruiter.db"
os.environ.setdefault("DATABASE_URL", DEFAULT_SQLITE_URL)

from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

import app.models  # noqa: E402, F401  — registra os modelos no metadata
from app.core.big_five import SJT_SCENARIOS  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.seed import seed_default_questionnaire  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402


async def main() -> None:
    url = settings.DATABASE_URL
    if not url.startswith("sqlite"):
        print(f"DATABASE_URL aponta para {url.split('://')[0]}, não para SQLite.")
        print("Para o banco de produção use as migrações: alembic upgrade head")
        raise SystemExit(1)

    engine = create_async_engine(url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()

    async with AsyncSessionLocal() as session:
        questionnaire = await seed_default_questionnaire(session)

    database_file = url.split("///")[-1]
    print(f"Banco local pronto: {database_file}")
    print(f"Instrumento padrão: {questionnaire.title}")
    print(f"Cenários: {len(SJT_SCENARIOS)} | Alternativas: {sum(len(s.options) for s in SJT_SCENARIOS)}")


if __name__ == "__main__":
    asyncio.run(main())
