# syntax=docker/dockerfile:1

# ---- builder: resolve as dependências num virtualenv isolado ----------------
# Os compiladores ficam só aqui; a imagem final não os carrega.
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Habilitado pelo docker compose de desenvolvimento, que roda pytest e ruff
# dentro do contêiner. A imagem publicada no Cloud Run nunca usa isto.
ARG INSTALL_DEV=false

WORKDIR /app
COPY requirements.txt requirements-dev.txt ./
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        pip install --no-cache-dir -r requirements-dev.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# ---- runtime ---------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080 \
    WEB_CONCURRENCY=2

RUN useradd --create-home --uid 1000 app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app . .

USER app

EXPOSE 8080

# `exec` mantém o uvicorn como PID 1: sem isso o SIGTERM enviado pelo Cloud Run
# na hora de escalar morre no shell e as requisições em voo são cortadas em vez
# de drenadas. A porta vem do ambiente porque o Cloud Run a injeta.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers ${WEB_CONCURRENCY}
