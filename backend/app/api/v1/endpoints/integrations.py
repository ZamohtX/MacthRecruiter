"""Endpoints da integração com o OxeTech Academy.

Expõem, dentro da própria API do produto, o pool de talentos do Academy: o
recrutador autenticado consulta os agregados do programa e a lista de alunos
disponíveis sem sair do MatchRecruiter. É a API pública sendo consumida e usada
em tempo real — não só num script.

Somente leitura e sob autenticação, coerente com o resto do produto. Falhas da
API externa viram 502 (culpa do upstream), não 500.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import get_current_user
from app.integrations.academy.client import AcademyAPIError, AcademyClient
from app.integrations.academy.schemas import AcademyAluno, AcademyStats
from app.models.user import User

router = APIRouter()


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
