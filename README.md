# MatchRecruiter

> **Contratar por lacuna, não por semelhança.**

Plataforma de recrutamento que trata a vaga como **função da lacuna do time**, e não como retrato
de um candidato ideal isolado.

## A ideia em um parágrafo

Antes de abrir a vaga, a equipe atual responde um **teste de julgamento situacional (SJT)
ancorado em Big Five**: 20 situações de trabalho, 4 condutas possíveis em cada, todas
profissionalmente defensáveis. A escolha pontua nos cinco fatores de personalidade, e as 10 soft
skills são derivadas deles. O candidato responde o **mesmo** instrumento. A plataforma compara os dois perfis, simula matematicamente como a média
do time muda **se aquela pessoa entrar**, e separa duas coisas que o mercado trata como uma só:

- **Fit complementar** — o candidato cobre as lacunas do time. É o que ranqueia.
- **Fit suplementar** — o candidato se parece com o time. Em excesso, significa contratar mais
  do mesmo: o time fica maior, não melhor.

Times criativos contratando mais criativos e times analíticos contratando mais analíticos é o
problema. Tornar essa diferença mensurável e visível é o produto.

## Estado do projeto

| Componente | Status |
| :--- | :--- |
| **Backend** (`backend/`) | MVP funcional — diagnóstico do time, perfil-alvo por lacuna, aplicação do teste, simulação pós-contratação, ranking e contratação |
| **Frontend** (`frontend/`) | MVP funcional — React 19 + TypeScript + Vite + React Router 8, cobrindo as telas de recrutador, integrante e candidato |
| Análise de CV/GitHub, micro-resumo por IA, análise de entrevista | Não iniciados — Etapas 3, 6 e 7 do fluxo completo |

## Documentação

| Documento | Conteúdo |
| :--- | :--- |
| [`backend/README.md`](backend/README.md) | Como rodar, endpoints, cálculo do fit e limitações conhecidas |
| [`frontend/README.md`](frontend/README.md) | Telas, decisões de interface e método de visualização de dados |
| [`docs/visao-de-negocio.md`](docs/visao-de-negocio.md) | Visão de negócio: problema, mercado, concorrência, riscos e decisões em aberto |
| [`docs/fluxo-mvp.md`](docs/fluxo-mvp.md) | Passo a passo executável do fluxo completo, com chamadas HTTP reais |
| [`docs/deploy-gcp.md`](docs/deploy-gcp.md) | Deploy no Google Cloud: Cloud Run, Cloud SQL, Firebase Hosting e segredos |

## Começando

Rode os dois comandos **em terminais separados**, cada um a partir da raiz do repositório.

### Sem Docker (mais rápido para desenvolver)

Banco SQLite local, nada além de Python e Node:

```bash
# terminal 1 — API em http://localhost:8000
cd backend
make dev-local

# terminal 2 — interface em http://localhost:5173
cd frontend
npm install && cp .env.example .env && npm run dev
```

### Com Docker (PostgreSQL, igual à produção)

Requer o daemon do Docker no ar — em distribuições com systemd,
`sudo systemctl start docker`.

```bash
# terminal 1
cd backend
cp .env.example .env
make bootstrap        # containers + migrações + seed

# terminal 2
cd frontend
npm install && cp .env.example .env && npm run dev
```

- Aplicação: http://localhost:5173
- Swagger: http://localhost:8000/docs

Sem `VITE_GOOGLE_CLIENT_ID` configurado, o login entra em modo de demonstração e usa os tokens
simulados do backend — dá para percorrer o fluxo inteiro sem credenciais do Google.

> `make dev-local` cria o schema a partir dos modelos e **contorna o Alembic**. É adequado para
> desenvolvimento e demo; PostgreSQL com `alembic upgrade head` continua sendo o caminho de
> produção, e é o que valida as migrações.

## Aviso sobre validade científica

O instrumento é uma **proposta de produto**, não uma medida psicometricamente validada. Ele está
ancorado em Big Five — o modelo de personalidade com maior base empírica — mas as cargas dos
fatores e os pesos das competências foram definidos por julgamento informado pela literatura,
**não estimados a partir de dados**.

Antes de qualquer uso comercial precisa de consistência interna, teste-reteste e validação
preditiva contra desempenho real. Há também uma limitação de método inerente ao formato de
escolha forçada (ipsatividade) que é mitigada, mas não eliminada — detalhes em
`backend/README.md` e em `docs/visao-de-negocio.md` §10.3.
