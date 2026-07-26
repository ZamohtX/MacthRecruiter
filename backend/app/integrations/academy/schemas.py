"""Modelos do payload da API do Academy.

Deliberadamente **tolerantes** (`extra="allow"`): a API é externa e versionada
por conta de terceiros, e no momento da integração ela devolvia coleções vazias
(0 alunos/empresas), então o formato exato de cada registro não pôde ser
observado em produção. Aceitamos as variações plausíveis de nome de campo e
normalizamos o que o produto realmente usa — id, nome e tecnologias — sem
quebrar quando um campo extra aparece.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AcademyStats(BaseModel):
    """Agregados de `GET /stats`."""

    empresas_ativas: int = 0
    alunos_habilitados: int = 0
    alunos_selecionados: int = 0
    alunos_disponiveis: int = 0

    model_config = ConfigDict(extra="allow")


class AcademyAluno(BaseModel):
    """Um aluno habilitado do programa.

    A API não expõe CPF, e-mail nem telefone — o contato é intermediado pela
    coordenação. Trabalhamos só com id, nome e as tecnologias declaradas, que é
    o "currículo" de hard skills que percorremos ao casar candidato e vaga.
    """

    id: int
    nome: str = ""
    modalidade: str | None = None
    turno: str | None = None
    disponivel: bool | None = None
    # Normalizado a partir de `tecnologias` (lista) ou `tecnologia` (string).
    techs: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")

    @field_validator("nome", mode="before")
    @classmethod
    def _clean_nome(cls, value: Any) -> str:
        return (value or "").strip()

    @classmethod
    def from_payload(cls, raw: dict[str, Any]) -> "AcademyAluno":
        """Constrói a partir do dicionário cru, normalizando as tecnologias.

        Os nomes de campo variam entre versões da API; aceitamos os candidatos
        mais prováveis e caímos para lista vazia quando nenhum está presente.
        """
        data = dict(raw)
        techs = _coerce_techs(
            data.get("techs") or data.get("tecnologias") or data.get("tecnologia") or data.get("skills")
        )
        data["techs"] = techs
        return cls.model_validate(data)

    @property
    def display_name(self) -> str:
        return self.nome or f"Aluno #{self.id}"


class AcademyEmpresa(BaseModel):
    """Empresa parceira de `GET /empresas`."""

    id: int
    nome: str = ""
    segmento: str | None = None
    modalidade: str | None = None

    model_config = ConfigDict(extra="allow")


class AcademyPage(BaseModel):
    """Envelope paginado padrão da API (`{"data": [...], "meta": {...}}`)."""

    data: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

    @property
    def page(self) -> int:
        return int(self.meta.get("page", 1))

    @property
    def total_pages(self) -> int:
        return int(self.meta.get("total_pages", 1))

    @property
    def total(self) -> int:
        return int(self.meta.get("total", len(self.data)))


def _coerce_techs(value: Any) -> list[str]:
    """Aceita lista, string separada por vírgula, ou lista de objetos {nome}."""
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        techs: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                techs.append(item.strip())
            elif isinstance(item, dict):
                name = item.get("nome") or item.get("name") or item.get("tecnologia")
                if name:
                    techs.append(str(name).strip())
        return techs
    return []
