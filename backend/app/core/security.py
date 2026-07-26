from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.core.config import MOCK_GOOGLE_CLIENT_ID, settings


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def _mock_login_allowed(id_token_str: str) -> bool:
    """O login simulado existe apenas fora de produção.

    Antes bastava o token começar com "mock_google_token": mesmo com um
    GOOGLE_CLIENT_ID real, qualquer pessoa forjava esse prefixo e recebia um
    JWT válido de um usuário arbitrário. O corte por ambiente é o que fecha
    isso — o prefixo sozinho nunca foi uma credencial.
    """
    if settings.is_production:
        return False
    return id_token_str.startswith("mock_google_token") or settings.GOOGLE_CLIENT_ID == MOCK_GOOGLE_CLIENT_ID


def verify_google_id_token(id_token_str: str) -> dict[str, Any]:
    """
    Verifies a Google OAuth2 ID Token.
    Supports real tokens via google.oauth2.id_token, and mock tokens for dev/testing.
    """
    if _mock_login_allowed(id_token_str):
        # Extract name/email from mock token if embedded, or return default mock payload
        parts = id_token_str.split("_")
        suffix = parts[-1] if len(parts) > 3 else "test"
        return {
            "sub": f"google_id_{suffix}",
            "email": f"user_{suffix}@example.com",
            "name": f"Test User {suffix.capitalize()}",
            "email_verified": True,
        }

    try:
        from google.auth.transport import requests
        from google.oauth2 import id_token

        id_info = id_token.verify_oauth2_token(id_token_str, requests.Request(), settings.GOOGLE_CLIENT_ID)
        return id_info
    except Exception as e:
        raise ValueError(f"Invalid Google ID token: {str(e)}") from e
