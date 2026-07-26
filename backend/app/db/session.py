from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine_kwargs: dict[str, Any] = {"echo": False, "future": True}

# SQLite (testes e `make dev-local`) usa pool próprio e recusa estes parâmetros;
# só o PostgreSQL de produção precisa deles.
if settings.DATABASE_URL.startswith("postgresql"):
    engine_kwargs |= {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_recycle": settings.DB_POOL_RECYCLE,
        # O Cloud SQL derruba conexões ociosas sem avisar o cliente: sem o
        # pre_ping a primeira query depois de um período parado falha.
        "pool_pre_ping": True,
    }

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
