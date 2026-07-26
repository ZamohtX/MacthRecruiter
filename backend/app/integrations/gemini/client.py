"""Cliente da API pública do Google Gemini (Generative Language).

Só o necessário para um resumo de texto: uma chamada `generateContent`,
autenticada por API key no header `x-goog-api-key` (não na URL, para a chave não
vazar em log de acesso). O modelo padrão é o `gemini-2.5-flash` — no projeto desta
chave o `2.0-flash` está com quota zerada.

    async with GeminiClient.from_settings() as gemini:
        texto = await gemini.generate(prompt)

Quem chama trata `GeminiError` caindo para um resumo-regra: o resumo é um apoio,
a falta dele nunca pode derrubar a tela do candidato.
"""

from typing import Any

import httpx

from app.core.config import settings

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiError(RuntimeError):
    """Falha ao falar com o Gemini (sem chave, quota, rede, resposta inesperada)."""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class GeminiClient:
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        *,
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        if not api_key:
            raise GeminiError("GEMINI_API_KEY não configurada.")
        self.model = model
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            timeout=timeout,
            transport=transport,
        )

    @classmethod
    def from_settings(cls, *, transport: httpx.AsyncBaseTransport | None = None) -> "GeminiClient":
        return cls(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL, transport=transport)

    async def __aenter__(self) -> "GeminiClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._client.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def generate(self, prompt: str, *, temperature: float = 0.4, max_output_tokens: int = 800) -> str:
        """Gera texto a partir de um prompt. Devolve o texto puro do candidato 0."""
        body: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
                # Os modelos 2.5 "pensam" antes de responder, e esses tokens de
                # raciocínio comem o teto de saída — num resumo curto isso truncava
                # a resposta no meio. Zerar o thinking dá o texto completo e mais rápido.
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
        try:
            response = await self._client.post(f"/models/{self.model}:generateContent", json=body)
        except httpx.HTTPError as exc:  # rede, timeout, DNS
            raise GeminiError(f"Falha de rede ao chamar o Gemini: {exc}") from exc

        if response.status_code == 429:
            raise GeminiError("Quota do Gemini atingida (429).", status_code=429)
        if response.status_code >= 400:
            raise GeminiError(
                f"Gemini respondeu {response.status_code}.", status_code=response.status_code
            )

        try:
            data = response.json()
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts).strip()
        except (ValueError, KeyError, IndexError) as exc:
            raise GeminiError(f"Resposta inesperada do Gemini: {exc}") from exc

        if not text:
            raise GeminiError("Gemini devolveu texto vazio.")
        return text
