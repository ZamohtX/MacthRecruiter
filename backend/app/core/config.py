from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Valores de desenvolvimento que não podem vazar para produção: são públicos
# (estão no repositório), então a validação abaixo recusa a subida com eles.
DEV_SECRET_KEY = "dev_secret_key_change_me_in_prod_987654321"
MOCK_GOOGLE_CLIENT_ID = "mock_google_client_id"


class Settings(BaseSettings):
    PROJECT_NAME: str = "MatchRecruiter API"
    API_V1_STR: str = "/api/v1"

    # Em "production" o login simulado é desligado e os defaults de dev viram
    # erro de inicialização. Ver `_reject_dev_defaults_in_production`.
    ENVIRONMENT: Literal["development", "production"] = "development"

    DATABASE_URL: str = "postgresql+asyncpg://matchuser:matchpassword@localhost:5432/matchrecruiter"

    # Pool aplicado apenas a PostgreSQL. Vários contêineres do Cloud Run
    # dividem o mesmo limite de conexões do Cloud SQL, então cada instância
    # segura poucas conexões e não usa overflow.
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 0
    DB_POOL_RECYCLE: int = 1800

    SECRET_KEY: str = DEV_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    GOOGLE_CLIENT_ID: str = MOCK_GOOGLE_CLIENT_ID

    # Origens permitidas no CORS. "*" apenas para desenvolvimento — com
    # allow_credentials=True o navegador rejeita o wildcard em produção.
    CORS_ORIGINS: list[str] = ["*"]

    # Cria/atualiza o questionário padrão na subida da aplicação. Sem ele não há
    # nenhuma pergunta cadastrada e o fluxo inteiro fica inutilizável.
    # Em produção use o job de release: com várias instâncias subindo em
    # paralelo o seed correria contra si mesmo a cada escala.
    AUTO_SEED: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @model_validator(mode="after")
    def _reject_dev_defaults_in_production(self) -> "Settings":
        """Falha na subida, e não silenciosamente em runtime.

        Cada item aqui é uma falha de segurança real se passar despercebida:
        JWT assinado com chave pública, login simulado aceito por qualquer um,
        ou CORS aberto para qualquer origem com credenciais.
        """
        if not self.is_production:
            return self

        problems: list[str] = []
        if self.SECRET_KEY == DEV_SECRET_KEY:
            problems.append("SECRET_KEY ainda é o valor de desenvolvimento — gere um segredo próprio")
        if self.GOOGLE_CLIENT_ID == MOCK_GOOGLE_CLIENT_ID:
            problems.append("GOOGLE_CLIENT_ID ainda é o mock — informe o client ID real do Google OAuth")
        if "*" in self.CORS_ORIGINS:
            problems.append('CORS_ORIGINS contém "*" — informe a origem exata do frontend')
        if self.DATABASE_URL.startswith("sqlite"):
            problems.append("DATABASE_URL aponta para SQLite — use o PostgreSQL gerenciado")

        if problems:
            raise ValueError(
                "Configuração inválida para ENVIRONMENT=production:\n  - " + "\n  - ".join(problems)
            )
        return self


settings = Settings()
