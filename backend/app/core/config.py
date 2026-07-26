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

    # Integração com a API pública de Desenvolvedores do OxeTech Academy.
    # O token é emitido uma única vez no painel do Academy e mora só no .env —
    # nunca no código. Sem token a integração fica inerte (o produto continua
    # funcionando sem ela). Ver app/integrations/academy/.
    ACADEMY_API_BASE_URL: str = "https://oxetech.al.gov.br/api/dev/v1"
    ACADEMY_API_TOKEN: str = ""
    # Teto de segurança para não estourar o limite de 120 req/min da API ao
    # paginar o pool de talentos.
    ACADEMY_MAX_ALUNOS: int = 100

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
