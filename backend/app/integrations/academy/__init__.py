"""Integração com a API pública de Desenvolvedores do OxeTech Academy.

A API (`/api/dev/v1`) é somente leitura e intermedia o encontro empresas ↔ alunos
habilitados do programa. Aqui ela vira **fonte de talentos** do MatchRecruiter:
os alunos disponíveis entram como candidatos, respondem o diagnóstico
comportamental e são ranqueados pelo mesmo motor de fit complementar do produto.

Camadas:

* `client`     — cliente HTTP assíncrono (autenticação, paginação, erros).
* `schemas`    — modelos Pydantic tolerantes do payload da API.
* `roster`     — pool sintético determinístico, usado quando a API não devolve
                 alunos (o programa pode estar entre turmas, sem ninguém
                 disponível — foi o caso observado em 26/07/2026).
* `simulator`  — orquestra importação → diagnóstico → vaga → ranqueamento.
"""

from app.integrations.academy.client import AcademyAPIError, AcademyClient
from app.integrations.academy.schemas import AcademyAluno, AcademyEmpresa, AcademyStats

__all__ = [
    "AcademyClient",
    "AcademyAPIError",
    "AcademyAluno",
    "AcademyEmpresa",
    "AcademyStats",
]
