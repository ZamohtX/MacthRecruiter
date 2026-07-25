.PHONY: help up down restart logs ps exec-api exec-db test test-local ruff-check ruff-format ruff-fix migrate makemigrations clean

# Standard shell setup
SHELL := /bin/bash

# Color helpers for clean terminal output
YELLOW := \033[0;33m
GREEN  := \033[0;32m
NC     := \033[0m

help: ## Exibe este menu de ajuda com todos os comandos disponíveis
	@echo -e "$(GREEN)MatchRecruiter Backend - Comandos Disponíveis:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-18s$(NC) %s\n", $$1, $$2}'

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

test-local: ## Executa os testes automatizados no ambiente virtual local (.venv)
	.venv/bin/pytest

ruff-check: ## Executa a verificação do linter Ruff
	.venv/bin/ruff check .

ruff-format: ## Formata o código fonte com Ruff
	.venv/bin/ruff format .

ruff-fix: ## Corrige automaticamente erros de lint apontados pelo Ruff
	.venv/bin/ruff check --fix .

migrate: ## Aplica as migrações do Alembic no banco de dados
	docker compose exec api alembic upgrade head

makemigrations: ## Gera um novo script de migração com o Alembic (Uso: make makemigrations m="nome_da_migracao")
	docker compose exec api alembic revision --autogenerate -m "$(m)"

clean: ## Limpa arquivos temporários e caches do Python/Pytest
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov .ruff_cache
