# MatchRecruiter API - Análise de Impacto & Fit Complementar de Soft Skills

Backend desenvolvido em Python com FastAPI, SQLAlchemy v2.0 (Async) e PostgreSQL para mapeamento comportamental de equipes, candidatura de talentos e **Simulação Pós-Contratação de Soft Skills**.

---

## 🎯 Sobre o Projeto

O **MatchRecruiter** resolve o desafio de montar equipes de alta performance identificando como um novo integrante afetará a média comportamental de um time antes mesmo da contratação.

### Fluxo da Aplicação:
1. **Mapeamento da Equipe Atual**: O recrutador cria um time e gera o link de convite. Os membros logam via Google OAuth e respondem ao questionário de soft skills. A API calcula a média comportamental do time.
2. **Candidatura & Avaliação**: O candidato se inscreve na vaga vinculada à equipe, loga via Google OAuth e responde ao mesmo questionário de soft skills.
3. **Simulação Pós-Contratação & Painel do Recrutador**: A API simula como a média do time irá mudar ($\text{Antes}$ vs. $\text{Depois}$), destaca lacunas preenchidas (*gaps filled*) e calcula o índice numérico de fit complementar.

---

## 🚀 Tecnologias Utilizadas

- **Linguagem**: Python 3.11+
- **Framework Web**: FastAPI
- **ORM**: SQLAlchemy v2.0 (Async)
- **Driver de Banco**: `asyncpg` e `aiosqlite` (para testes isolados)
- **Banco de Dados**: PostgreSQL 16
- **Migrations**: Alembic
- **Autenticação**: Google OAuth2 (`id_token`) + JWT Bearer Token
- **Infraestrutura**: Docker & Docker Compose
- **Testes & Qualidade**: Pytest, HTTPX AsyncClient e Ruff Linter

---

## 📋 Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (com integração WSL2 ativada se estiver no Linux/Ubuntu)
- `make` (opcional, mas recomendado)
- Python 3.11+ (caso queira rodar os testes localmente sem Docker)

---

## 🛠️ Como Executar a Aplicação

### Opção 1: Via Docker Compose (Recomendado)

1. Clone o repositório e acesse a pasta `backend`:
   ```bash
   cd backend
   ```

2. Crie o arquivo de ambiente `.env` (ou utilize as configurações padrão):
   ```bash
   cp .env.example .env
   ```

3. Inicie os containers com o Makefile:
   ```bash
   make up
   ```
   *(Ou diretamente via Docker: `docker compose up --build -d`)*

4. A API estará pronta e acessível em:
   - **Documentação Interativa (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Documentação ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
   - **Healthcheck**: [http://localhost:8000/health](http://localhost:8000/health)

---

### Opção 2: Execução Local (Desenvolvimento)

1. Crie e ative o ambiente virtual Python:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Inicie o servidor em modo de desenvolvimento:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## 🧪 Testes Automatizados

A suíte de testes cobre os fluxos de sucesso (200/201), erros de validação (422), acesso não autorizado (401), recursos não encontrados (404) e o teste de integração de ponta a ponta (End-to-End).

- **Executar os testes no ambiente local**:
  ```bash
  make test-local
  ```

- **Executar os testes dentro do container Docker**:
  ```bash
  make test
  ```

- **Verificar e formatar o código com o Ruff**:
  ```bash
  make ruff-check
  make ruff-fix
  ```

---

## 📌 Endpoints Chave da API

### 1. Autenticação Google & Cadastro Automático
- `POST /api/v1/auth/google`
  - **Descrição**: Autentica o `id_token` do Google e retorna o token JWT local.
  - **Parâmetros Opcionais**:
    - `invite_token`: vincula o usuário diretamente à equipe como `MEMBER`.
    - `job_id`: vincula o usuário à vaga como `CANDIDATE`.

### 2. Mapeamento de Soft Skills do Time
- `GET /api/v1/teams/{id}/soft-skills-profile`
  - **Descrição**: Retorna o número de integrantes e as notas médias da equipe agrupadas por dimensão comportamental (ex: Comunicação, Liderança, Adaptabilidade).

### 3. Simulação Pós-Contratação & Análise de Impacto
- `POST /api/v1/jobs/{job_id}/candidates/{candidate_id}/impact-analysis`
  - **Descrição**: Compara o perfil do candidato com a equipe atual e calcula a **simulação matemática da média pós-contratação**:
    $$\text{Média Simulação}[d] = \frac{(\text{Média Atual}[d] \times N) + \text{Nota do Candidato}[d]}{N + 1}$$
  - **Retorno**: Pontuação do candidato, média atual do time, simulação pós-contratação, deltas ($\Delta$), lacunas preenchidas (*gaps filled*) e índice de fit (0-100).

### 4. Painel do Recrutador
- `GET /api/v1/jobs/{job_id}/candidates`
  - **Descrição**: Lista todos os candidatos da vaga com o status da candidatura (`APPLIED`, `SOFT_SKILLS_COMPLETED`, `UNDER_REVIEW`, `REJECTED`, `HIRED`), indicador de conclusão do teste e resumo do fit comportamental.

---

## 🛠️ Tabela de Comandos Makefile

| Comando | Descrição |
| :--- | :--- |
| `make up` | Constrói e inicia os containers da API e do PostgreSQL em segundo plano |
| `make down` | Para e remove os containers e redes Docker |
| `make down-v` | Para containers e apaga o volume de dados do banco de dados |
| `make logs` | Acompanha os logs unificados da aplicação em tempo real |
| `make ps` | Exibe o status dos containers |
| `make exec-api` | Abre o terminal bash no container da API |
| `make exec-db` | Conecta ao console `psql` do PostgreSQL |
| `make test` | Roda a suíte de testes com Pytest |
| `make ruff-check` | Executa a verificação estática de linting |
| `make ruff-fix` | Corrige problemas de formatação e importação automaticamente |
