from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MatchRecruiter API"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = "postgresql+asyncpg://matchuser:matchpassword@localhost:5432/matchrecruiter"

    SECRET_KEY: str = "dev_secret_key_change_me_in_prod_987654321"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    GOOGLE_CLIENT_ID: str = "mock_google_client_id"

    # Origens permitidas no CORS. "*" apenas para desenvolvimento — com
    # allow_credentials=True o navegador rejeita o wildcard em produção.
    CORS_ORIGINS: list[str] = ["*"]

    # Cria/atualiza o questionário padrão na subida da aplicação. Sem ele não há
    # nenhuma pergunta cadastrada e o fluxo inteiro fica inutilizável.
    AUTO_SEED: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
