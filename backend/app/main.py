import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.seed import seed_default_questionnaire
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    if settings.AUTO_SEED:
        try:
            async with AsyncSessionLocal() as session:
                await seed_default_questionnaire(session)
        except Exception:  # noqa: BLE001 - a API deve subir mesmo sem banco pronto
            logger.exception("Falha ao aplicar o seed do questionário padrão.")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Recrutamento por complementaridade: o time responde o diagnóstico comportamental "
        "antes da vaga abrir, o candidato responde o mesmo instrumento, e a API simula o "
        "perfil do time pós-contratação para evitar fit suplementar em excesso."
    ),
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "project": settings.PROJECT_NAME}
