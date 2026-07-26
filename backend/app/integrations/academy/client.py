"""Cliente HTTP da API de Desenvolvedores do OxeTech Academy.

Somente leitura, autenticada por Bearer token, paginada (`page`/`per_page`, máx.
100 por página) e limitada a 120 req/min. O cliente não guarda estado entre
chamadas além da configuração; use como context manager assíncrono para fechar a
conexão.

    async with AcademyClient.from_settings() as academy:
        stats = await academy.stats()
        alunos = await academy.list_alunos_all(disponivel=True)
"""

from typing import Any

import httpx

from app.core.config import settings
from app.integrations.academy.schemas import (
    AcademyAluno,
    AcademyEmpresa,
    AcademyPage,
    AcademyStats,
)

# Teto duro imposto pela própria API — pedir mais que isso por página é rejeitado.
MAX_PER_PAGE = 100


class AcademyAPIError(RuntimeError):
    """Falha ao falar com a API do Academy (rede, auth, status não-2xx)."""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class AcademyClient:
    def __init__(
        self,
        token: str,
        base_url: str = "https://oxetech.al.gov.br/api/dev/v1",
        *,
        timeout: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        if not token:
            raise AcademyAPIError(
                "ACADEMY_API_TOKEN não configurado. Gere um token no painel de "
                "Desenvolvedores do Academy e coloque-o no .env."
            )
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=timeout,
            transport=transport,
        )

    @classmethod
    def from_settings(cls, *, transport: httpx.AsyncBaseTransport | None = None) -> "AcademyClient":
        return cls(
            token=settings.ACADEMY_API_TOKEN,
            base_url=settings.ACADEMY_API_BASE_URL,
            transport=transport,
        )

    async def __aenter__(self) -> "AcademyClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Chamada crua
    # ------------------------------------------------------------------

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            response = await self._client.get(path, params=_clean_params(params))
        except httpx.HTTPError as exc:  # rede, timeout, DNS
            raise AcademyAPIError(f"Falha de rede ao chamar {path}: {exc}") from exc

        if response.status_code == 401:
            raise AcademyAPIError("Token do Academy inválido ou expirado (401).", status_code=401)
        if response.status_code == 429:
            raise AcademyAPIError("Limite de requisições do Academy atingido (429).", status_code=429)
        if response.status_code >= 400:
            raise AcademyAPIError(
                f"API do Academy respondeu {response.status_code} em {path}.",
                status_code=response.status_code,
            )
        try:
            return response.json()
        except ValueError as exc:
            raise AcademyAPIError(f"Resposta não-JSON de {path}.") from exc

    # ------------------------------------------------------------------
    # Endpoints
    # ------------------------------------------------------------------

    async def ping(self) -> dict[str, Any]:
        """Testa conexão e token. Devolve o payload cru (`{ok, versao, aluno}`)."""
        return await self._get("/ping")

    async def stats(self) -> AcademyStats:
        return AcademyStats.model_validate(await self._get("/stats"))

    async def list_alunos(
        self,
        *,
        tecnologia: str | None = None,
        modalidade: str | None = None,
        turno: str | None = None,
        disponivel: bool | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> AcademyPage:
        return AcademyPage.model_validate(
            await self._get(
                "/alunos",
                {
                    "tecnologia": tecnologia,
                    "modalidade": modalidade,
                    "turno": turno,
                    "disponivel": _as_bool_param(disponivel),
                    "page": page,
                    "per_page": min(per_page, MAX_PER_PAGE),
                },
            )
        )

    async def list_alunos_all(self, *, max_items: int = 100, **filters: Any) -> list[AcademyAluno]:
        """Percorre a paginação e devolve alunos já normalizados, até `max_items`."""
        collected: list[AcademyAluno] = []
        page = 1
        per_page = min(max_items, MAX_PER_PAGE)
        while len(collected) < max_items:
            envelope = await self.list_alunos(page=page, per_page=per_page, **filters)
            if not envelope.data:
                break
            for raw in envelope.data:
                collected.append(AcademyAluno.from_payload(raw))
                if len(collected) >= max_items:
                    break
            if page >= envelope.total_pages:
                break
            page += 1
        return collected

    async def list_empresas(
        self,
        *,
        segmento: str | None = None,
        modalidade: str | None = None,
        busca: str | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> list[AcademyEmpresa]:
        envelope = AcademyPage.model_validate(
            await self._get(
                "/empresas",
                {
                    "segmento": segmento,
                    "modalidade": modalidade,
                    "busca": busca,
                    "page": page,
                    "per_page": min(per_page, MAX_PER_PAGE),
                },
            )
        )
        return [AcademyEmpresa.model_validate(item) for item in envelope.data]


def _clean_params(params: dict[str, Any] | None) -> dict[str, Any]:
    """Remove chaves None — a API trata parâmetro ausente e parâmetro vazio
    de formas diferentes, e mandar `disponivel=None` filtraria errado."""
    if not params:
        return {}
    return {k: v for k, v in params.items() if v is not None}


def _as_bool_param(value: bool | None) -> str | None:
    if value is None:
        return None
    return "true" if value else "false"
