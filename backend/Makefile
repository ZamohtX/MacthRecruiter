.PHONY: help venv dev-local up down down-v restart logs ps exec-api exec-db test test-local ruff-check ruff-format ruff-fix migrate downgrade seed seed-local bootstrap makemigrations clean

# Standard shell setup
SHELL := /bin/bash

# Banco local usado pelos alvos sem Docker.
SQLITE_URL := sqlite+aiosqlite:///./matchrecruiter.db

# Color helpers for clean terminal output
YELLOW := \033[0;33m
GREEN  := \033[0;32m
NC     := \033[0m

help: ## Exibe este menu de ajuda com todos os comandos disponíveis
	@echo -e "$(GREEN)MatchRecruiter Backend - Comandos Disponíveis:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-18s$(NC) %s\n", $$1, $$2}'

venv: ## Cria o ambiente virtual local e instala as dependências
	@test -d .venv || python3 -m venv .venv
	@.venv/bin/pip install -q -r requirements.txt
	@echo -e "$(GREEN)Ambiente pronto em .venv$(NC)"

dev-local: venv ## Sobe a API sem Docker, com banco SQLite local (dev e demo)
	@DATABASE_URL=$(SQLITE_URL) .venv/bin/python scripts/dev_local.py
	@echo -e "$(GREEN)API em http://localhost:8000/docs$(NC)"
	@DATABASE_URL=$(SQLITE_URL) .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

up: ## Sobe os containers Docker em segundo plano (build + up)
	docker compose up --build -d

down: ## Para e remove todos os containers e redes Docker
	docker compose down

down-v: ## Para e remove containers, redes e volumes persistentes
	docker compose down -v

restart: ## Reinicia os containers Docker
	docker compose restart

logs: ## Exibe os logs dos containers em tempo real (tail)
	docker compose logs -f

ps: ## Lista o status dos containers do docker compose
	docker compose ps

exec-api: ## Abre um shell bash dentro do container da API
	docker compose exec api bash

exec-db: ## Conecta via psql dentro do container do banco de dados PostgreSQL
	docker compose exec db psql -U matchuser -d matchrecruiter

test: ## Executa os testes automatizados dentro do container Docker da API
	docker compose exec api pytest

test-local: venv ## Executa os testes automatizados no ambiente virtual local (.venv)
	.venv/bin/pytest

ruff-check: ## Executa a verificação do linter Ruff
	.venv/bin/ruff check .

ruff-format: ## Formata o código fonte com Ruff
	.venv/bin/ruff format .

ruff-fix: ## Corrige automaticamente erros de lint apontados pelo Ruff
	.venv/bin/ruff check --fix .

migrate: ## Aplica as migrações do Alembic no banco de dados
	docker compose exec api alembic upgrade head

downgrade: ## Reverte a última migração do Alembic
	docker compose exec api alembic downgrade -1

seed: ## Cria/atualiza o questionário padrão de 10 soft skills (idempotente)
	docker compose exec api python -m app.db.seed

seed-local: venv ## Roda o seed usando o ambiente virtual local (.venv)
	DATABASE_URL=$(SQLITE_URL) .venv/bin/python -m app.db.seed

bootstrap: up migrate seed ## Sobe tudo do zero: containers + migrações + seed
	@echo -e "$(GREEN)Pronto. Swagger em http://localhost:8000/docs$(NC)"

makemigrations: ## Gera um novo script de migração com o Alembic (Uso: make makemigrations m="nome_da_migracao")
	docker compose exec api alembic revision --autogenerate -m "$(m)"

clean-db: ## Apaga o banco SQLite local
	rm -f matchrecruiter.db

clean: ## Limpa arquivos temporários e caches do Python/Pytest
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov .ruff_cache
