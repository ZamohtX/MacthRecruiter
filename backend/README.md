# MatchRecruiter API — Diagnóstico de Time e Fit Complementar

Backend em Python com FastAPI, SQLAlchemy 2.0 (Async) e PostgreSQL.

> **Contratar por lacuna, não por semelhança.**
> O time responde um teste situacional (SJT) ancorado em **Big Five** antes do processo
> seletivo. O candidato responde o **mesmo** instrumento. A API compara os dois perfis, simula
> o time pós-contratação e mede se a pessoa **cobre as lacunas** ou apenas **reforça o que o
> time já faz bem**.

---

## 🎯 O problema que a API resolve

Processos seletivos otimizam o indivíduo e ignoram a composição do time. O resultado é a
homogeneização: times analíticos contratam mais analíticos, e a lacuna que trava a entrega
nunca é preenchida. É o **fit suplementar em excesso**.

A API mede as duas coisas separadamente e deixa a diferença explícita:

| Métrica | O que significa | Como usar |
| :--- | :--- | :--- |
| `complementary_fit_score` (0–100) | Quanto o candidato **cobre as lacunas** do time | É o critério de ranqueamento |
| `supplementary_fit_index` (0–100) | Quanto o candidato **se parece** com o time | Alto + fit complementar baixo = mais do mesmo |

Índice suplementar alto com fit complementar baixo dispara o veredito
`EXCESSIVE_SUPPLEMENTARY` — exatamente o caso que o produto existe para evitar.

---

## 🔄 Fluxo da aplicação

```
[1] Diagnóstico do Time  →  [2] Perfil-alvo por Lacuna  →  [3] Candidatura
    (antes da vaga)             (pesos por déficit)           (mesmo teste)
                                                                   ↓
[6] Contratação          ←  [5] Painel do Recrutador   ←  [4] Simulação
    (entra no time)          (ranking por fit)             pós-contratação
```

1. **Diagnóstico do time** — o recrutador cria o time e gera um link de convite. Ele fica como
   responsável e **não** compõe o diagnóstico; os integrantes entram pelo convite e respondem os
   20 cenários do instrumento padrão. A API calcula o perfil médio e reporta **quantas pessoas
   efetivamente responderam**.
2. **Perfil-alvo por lacuna** — as dimensões em que o time fica abaixo do próprio centro viram
   os critérios de maior peso da vaga, cada peso com justificativa rastreável.
3. **Candidatura** — o candidato se inscreve na vaga e responde o mesmo instrumento.
4. **Simulação pós-contratação** — `(média_atual × N + nota_candidato) / (N + 1)` por dimensão,
   com deltas, lacunas cobertas, lacunas ainda descobertas e redundâncias.
5. **Painel do recrutador** — candidatos ranqueados por fit complementar, com filtros.
6. **Contratação** — o candidato entra no time e passa a compor o diagnóstico. O ciclo recomeça.

### O instrumento: SJT ancorado em Big Five

**Duas camadas, não duas alternativas.** Big Five é o *modelo de traço* — o que se mede. SJT
(*Situational Judgment Test*) é o *formato do item* — como se mede. Os dois se combinam:

```
resposta SJT   →   5 fatores Big Five   →   10 soft skills   →   lacuna / fit
(conduta que a     (camada latente,         (camada legível      (produto)
 pessoa escolhe)    com literatura)          para o gestor)
```

**20 cenários, 4 condutas cada.** Todas as alternativas são profissionalmente defensáveis: a
diferença entre elas é de ênfase de traço, não de qualidade. Não existe opção obviamente certa
a marcar — é isso que torna o formato mais difícil de gamear que "Sou organizado: 1 a 5".

| Camada | Conteúdo | Onde |
| :--- | :--- | :--- |
| **Fatores Big Five** | Abertura à Experiência · Conscienciosidade · Extroversão · Amabilidade · Estabilidade Emocional | `app/core/big_five.py` |
| **Soft skills derivadas** | Comunicação · Colaboração · Disciplina e Organização · Criatividade e Inovação · Pensamento Analítico · Adaptabilidade · Liderança e Influência · Proatividade e Autonomia · Resiliência sob Pressão · Aprendizado Contínuo | `app/core/soft_skills.py` |
| **Conversão** | Escolhas → fatores → competências | `app/services/scoring.py` |

Cada competência é uma combinação ponderada de fatores cujos pesos somam 1.0 — por isso a
competência derivada permanece na mesma escala 1–5 dos fatores. Exemplo: *Disciplina e
Organização* = 0.80 × Conscienciosidade + 0.20 × Estabilidade Emocional.

**As cargas nunca são expostas ao respondente.** Se o candidato vir que uma alternativa pontua
Conscienciosidade, ele escolhe pelo rótulo — exatamente a desejabilidade social que o formato
existe para evitar. A chave de correção fica auditável no banco (`option_trait_loadings`).

> ⚠️ **Este instrumento não é psicometricamente validado.** As cargas dos fatores e os pesos das
> competências são uma proposta de produto informada pelo padrão da literatura, **não
> coeficientes empíricos**. Antes de uso comercial precisa de consistência interna, teste-reteste
> e validação preditiva contra desempenho real. Ver `docs/visao-de-negocio.md` §10.3.

#### A escala é normativa, não absoluta

A pontuação de cada fator é ancorada no **nível de acaso**: 3.0 significa "escolhe as condutas
deste fator na frequência que o acaso produziria", 5.0 "sempre", 1.0 "nunca".

Isso importa para interpretar qualquer número da API: **4.2 em Conscienciosidade não quer dizer
"domina a competência"**, quer dizer "escolhe condutas conscienciosas bem mais que o acaso".

#### Limitação de método: ipsatividade

O formato de escolha forçada produz medidas parcialmente **ipsativas** — escolher uma conduta
implica não escolher as outras, então ser forte num fator empurra os demais para baixo. Isso
complica a comparação entre pessoas, que é exatamente o que este produto faz.

Três mitigações aplicadas:

1. **Cargas graduadas e sobrepostas** — uma alternativa carrega 1.0 no fator primário e, por
   exemplo, 0.4 num secundário. A soma dos fatores não é constante entre respondentes.
2. **Normalização por fator contra o nível de acaso**, não contra o total do respondente.
3. **Classificação relativa ao perfil do time** (ver abaixo), que não depende de limiares
   absolutos.

Reduz o problema; não o elimina. Validação empírica continua pendente.

---

## 🧮 Como o fit complementar é calculado

`app/services/fit_engine.py` — módulo puro, sem I/O, testado isoladamente em
`tests/fit_engine_test.py`. Limiares em `app/core/soft_skills.py`.

**Lacuna e força são posições dentro do perfil do time, não notas absolutas.** Uma dimensão é
lacuna quando fica meio desvio-padrão abaixo do centro do próprio perfil daquele time, e força
quando fica meio desvio acima.

Limiar fixo não funciona com um instrumento normativo e ipsativo: a média de um time diverso
regride ao centro por construção, então um corte absoluto em 3.5 classificaria *toda* dimensão
de *todo* time equilibrado como lacuna, e nenhuma como força. Comparar cada dimensão com o
centro do próprio time é, além disso, o que a expressão "lacuna do time" significa.

| Constante | Valor | Significado |
| :--- | :--- | :--- |
| `RELATIVE_BAND` | 0.5 | Desvios-padrão do centro do time para virar lacuna ou força |
| `MIN_MEANINGFUL_SPREAD` | 0.15 | Abaixo disso o time é uniforme: sem lacunas nem forças |
| `MIN_CANDIDATE_FLOOR` | 2.0 | Piso **absoluto** — mede ausência da competência, não posição relativa |
| `MIN_RESPONDENTS_FOR_CONFIDENCE` | 4 | Abaixo disso o diagnóstico sai marcado como baixa confiança |

`RELATIVE_BAND` e `MIN_CANDIDATE_FLOOR` são calibrações a validar com dado real, não valores
derivados.

O score combina três componentes, cada um normalizado de 0 a 1:

| Componente | Peso | O que mede |
| :--- | :--- | :--- |
| `gap_coverage` | 0.55 | Quanto das lacunas o candidato cobre, ponderado pelo tamanho de cada lacuna |
| `balance_gain` | 0.20 | Redução do desequilíbrio do perfil, normalizada pelo melhor candidato possível |
| `1 - redundancy` | 0.25 | O quanto o candidato **não** apenas duplica força existente |

Componentes não calculáveis (time sem lacuna, sem desequilíbrio) saem da conta e os pesos
restantes são renormalizados.

### Guarda-corpos

- **Piso mínimo por competência.** A penalidade exige três condições juntas: a competência está
  ausente no time (abaixo de 2.0), o candidato também não a tem, **e** ele a deixa como
  encontrou. As três importam — com escolha forçada todo respondente fica baixo em alguma
  dimensão, então punir "candidato abaixo do piso" isoladamente reprovaria todo mundo; e quem
  puxa a dimensão para cima, ainda que sem atingir o piso, está ajudando. Quando as três
  condições ocorrem, o veredito vira `BELOW_MINIMUM` e o score é limitado a 55.
- **Sem diagnóstico, sem comparação.** Se ninguém do time respondeu, o veredito é
  `INSUFFICIENT_TEAM_DATA` e a resposta diz explicitamente que aquilo não é complementaridade.
- **Explicabilidade.** Todo resultado traz `insights[]` com uma frase por dimensão explicando o
  porquê, e `risk_flags[]` com os alertas.

### Vereditos

| Veredito | Quando |
| :--- | :--- |
| `COMPLEMENTARY` | Cobertura de lacunas ≥ 0.6 |
| `BALANCED` | Contribui, mas sem cobrir lacuna de forma decisiva |
| `EXCESSIVE_SUPPLEMENTARY` | Redundância ≥ 0.70 e cobertura ≤ 0.35 — mais do mesmo |
| `BELOW_MINIMUM` | Abaixo do piso numa dimensão que já é lacuna |
| `INSUFFICIENT_TEAM_DATA` | Nenhum integrante respondeu ao diagnóstico |

---

## 🚀 Tecnologias

- **Linguagem**: Python 3.11+
- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2.0 (Async) · **Migrations**: Alembic
- **Banco**: PostgreSQL 16 (`asyncpg`) · `aiosqlite` nos testes
- **Auth**: Google OAuth2 (`id_token`) + JWT Bearer
- **Infra**: Docker & Docker Compose
- **Qualidade**: Pytest, HTTPX AsyncClient, Ruff

---

## 🛠️ Como executar

### Opção 1 — Sem Docker, com SQLite (mais rápido para desenvolver)

```bash
cd backend
make dev-local        # cria .venv, monta o banco local, aplica o seed e sobe a API
```

Um comando, sem daemon nem container. O banco fica em `matchrecruiter.db`; `make clean-db` apaga.

> ⚠️ `dev-local` cria o schema a partir de `Base.metadata` e **contorna o Alembic**. Uma migração
> quebrada não seria percebida por aqui — por isso a Opção 2 é o que valida as migrações e o que
> o CI deve exercitar.

### Opção 2 — Docker Compose, com PostgreSQL (igual à produção)

Requer o daemon do Docker no ar. Em distribuições com systemd:

```bash
sudo systemctl start docker      # e `enable` se quiser no boot
```

```bash
cd backend
cp .env.example .env
make bootstrap        # sobe containers + aplica migrações + roda o seed
```

### Opção 3 — Manual

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head          # precisa de um PostgreSQL acessível
python -m app.db.seed
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Em qualquer opção:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Healthcheck**: http://localhost:8000/health

### O seed é obrigatório

Sem ele **não existe nenhuma pergunta cadastrada** e o fluxo inteiro fica inutilizável. Com
`AUTO_SEED=true` (padrão) a aplicação cria/atualiza o questionário padrão a cada boot. O seed é
idempotente — nunca duplica itens.

---

## 🧪 Testes

```bash
make test         # dentro do container
make test-local   # no .venv local
make ruff-check   # linter
```

Cobertura: fluxos de sucesso (200/201), validação (422), não autorizado (401), **proibido (403)**,
não encontrado (404), regras do motor de fit e um teste ponta a ponta que prova a tese do produto
(`test_complementary_candidate_outranks_redundant_one`).

---

## 📌 Endpoints

### Autenticação

| Método | Rota | Descrição |
| :--- | :--- | :--- |
| `POST` | `/api/v1/auth/google` | Autentica o `id_token` do Google e devolve o JWT local. `invite_token` vincula ao time como `MEMBER`; `job_id` vincula à vaga como `CANDIDATE` |
| `GET` | `/api/v1/auth/me` | Usuário autenticado |

Em desenvolvimento (`GOOGLE_CLIENT_ID=mock_google_client_id`), qualquer token no formato
`mock_google_token_<sufixo>` cria/loga um usuário determinístico.

### Teste situacional — Etapa 1 (o time responde antes da vaga)

| Método | Rota | Descrição |
| :--- | :--- | :--- |
| `GET` | `/api/v1/questionnaires` | Lista os instrumentos disponíveis |
| `GET` | `/api/v1/questionnaires/default` | Instrumento padrão: 20 cenários com 4 condutas cada, sem as cargas dos fatores |
| `GET` | `/api/v1/questionnaires/{id}` | Um instrumento específico |
| `POST` | `/api/v1/questionnaires/{id}/answers` | Envia as condutas escolhidas (`question_id` + `selected_option_id`). Aceita envio parcial; reenviar **troca** a escolha em vez de duplicar |
| `GET` | `/api/v1/questionnaires/{id}/my-progress` | Progresso + perfil Big Five + soft skills derivadas da própria pessoa |
| `GET` | `/api/v1/questionnaires/{id}/my-answers` | Escolhas já enviadas — permite retomar o teste |

Envio de resposta:

```jsonc
{ "answers": [ { "question_id": "…", "selected_option_id": "…" } ] }
```

Alternativa que não pertence ao cenário informado é rejeitada com **400** — aplicaria cargas
erradas ao perfil.

### Times — Etapas 1 e 2

| Método | Rota | Descrição |
| :--- | :--- | :--- |
| `POST` | `/api/v1/teams` | Cria o time. Quem cria fica como **responsável, não integrante** — não responde o diagnóstico nem entra na média |
| `GET` | `/api/v1/teams` | Times que a pessoa possui ou dos quais participa |
| `POST` | `/api/v1/teams/{id}/invites` | Gera link de convite (`expires_in_days`, padrão 30) |
| `GET` | `/api/v1/teams/{id}/soft-skills-profile` | Perfil agregado nas duas camadas (`trait_scores` e `dimension_scores`) + `respondent_count`, `dispersion` e alerta de baixa confiança |
| `GET` | `/api/v1/teams/{id}/diagnostic-status` | Quem já respondeu e se a vaga pode ser aberta |
| `GET` | `/api/v1/teams/{id}/gap-analysis` | **Perfil-alvo por lacuna**: pesos por dimensão, justificativa de cada peso e piso mínimo |

### Vagas e candidatura — Etapas 3 a 6

| Método | Rota | Descrição |
| :--- | :--- | :--- |
| `POST` | `/api/v1/jobs` | Abre a vaga. Sem `questionnaire_id`, usa o instrumento padrão |
| `GET` | `/api/v1/jobs` | Vagas dos times de que a pessoa é responsável |
| `GET` | `/api/v1/jobs/{id}` | Detalhe da vaga (visível ao candidato) |
| `GET` | `/api/v1/jobs/{id}/questionnaire` | Instrumento que o candidato deve responder — o mesmo aplicado ao time |
| `POST` | `/api/v1/jobs/{id}/apply` | Candidatura |
| `POST` | `/api/v1/jobs/{id}/answers` | Escolhas do candidato. Só marca `SOFT_SKILLS_COMPLETED` quando **todos** os cenários forem respondidos |
| `GET` | `/api/v1/jobs/{id}/my-progress` | Progresso do próprio candidato |

### Painel do recrutador

| Método | Rota | Descrição |
| :--- | :--- | :--- |
| `GET` | `/api/v1/jobs/{id}/candidates` | Candidatos ranqueados por fit complementar |
| `POST` | `/api/v1/jobs/{id}/candidates/{cid}/impact-analysis` | Simulação pós-contratação completa |
| `PATCH` | `/api/v1/jobs/{id}/candidates/{cid}/status` | Move a candidatura no funil |
| `POST` | `/api/v1/jobs/{id}/candidates/{cid}/hire` | Contrata: marca `HIRED` e adiciona ao time |

**Filtros de `/candidates`**: `min_fit_score` (0–100), `status`, `limit`, `sort_desc`.
Quem ainda não respondeu o teste fica no fim da lista em ambas as ordenações.

**Autorização**: dados de candidato são restritos ao responsável pelo time da vaga (403 caso
contrário). O perfil do time é visível a quem participa dele.

---

## 📐 Exemplo — simulação pós-contratação

`POST /api/v1/jobs/{job_id}/candidates/{candidate_id}/impact-analysis`

Exemplo reduzido a 4 dimensões para caber na página — valores calculados pelo motor real.
O time é forte em Criatividade e Análise, fraco em Colaboração e Comunicação; a candidata é o
espelho disso.

```jsonc
{
  "candidate_name": "Ana Souza",
  "current_team_scores": {
    "Colaboração": 1.24, "Comunicação": 1.86,
    "Criatividade e Inovação": 4.04, "Pensamento Analítico": 3.51
  },
  "candidate_scores": {
    "Colaboração": 3.79, "Comunicação": 3.45,
    "Criatividade e Inovação": 1.60, "Pensamento Analítico": 1.14
  },
  "simulation": {
    "current_team_size": 4,
    "new_team_size": 5,
    "simulated_team_scores": {
      "Colaboração": 1.75, "Comunicação": 2.18,
      "Criatividade e Inovação": 3.55, "Pensamento Analítico": 3.04
    },
    "score_deltas": {
      "Colaboração": 0.51, "Comunicação": 0.32,
      "Criatividade e Inovação": -0.49, "Pensamento Analítico": -0.47
    },
    "gaps_filled": ["Colaboração", "Comunicação"],
    "gaps_missed": [],
    "overlaps": []
  },
  "fit_score": 78.9,
  "complementary_fit_score": 78.9,
  "supplementary_fit_index": 44.1,
  "gap_coverage": 0.616,
  "balance_gain": 1.0,
  "redundancy": 0.0,
  "verdict": "COMPLEMENTARY",
  "risk_flags": [
    "Candidato abaixo do piso mínimo (2.0) em Pensamento Analítico: 1.1 — o time cobre (3.5), mas a média cai."
  ],
  "insights": [
    {
      "dimension": "Colaboração",
      "status": "GAP",
      "contribution": "FILLS_GAP",
      "explanation": "Colaboração é lacuna do time (1.2) e o candidato pontua 3.8 — cobre a lacuna."
    },
    {
      "dimension": "Pensamento Analítico",
      "status": "STRENGTH",
      "contribution": "DILUTES_STRENGTH",
      "explanation": "Pensamento Analítico é força do time (3.5), mas o candidato pontua 1.1 e puxa a média para baixo."
    }
  ]
}
```

Repare que **duas dimensões caem** (−0.49 e −0.47). Isso é esperado e está correto: a candidata
é fraca justamente onde o time é forte. O produto mostra o custo junto com o ganho — um resumo
só elogioso destruiria a confiança do recrutador.

---

## 🗂️ Estrutura

```
app/
├── core/
│   ├── config.py          Settings (env)
│   ├── deps.py            Dependências de autenticação
│   ├── security.py        JWT + verificação do token Google
│   ├── big_five.py        ⭐ Fatores, banco de 20 cenários SJT e cargas — o instrumento
│   └── soft_skills.py     10 competências derivadas + limiares do diagnóstico
├── db/
│   ├── base.py, session.py
│   └── seed.py            Seed idempotente do questionário padrão
├── models/                SQLAlchemy (user, team, questionnaire, job)
├── repositories/          Acesso a dados
├── schemas/               Pydantic (contratos da API)
├── services/
│   ├── fit_engine.py      ⭐ Regra de negócio central — módulo puro
│   ├── scoring.py         ⭐ SJT → Big Five → soft skills — módulo puro
│   ├── soft_skills_service.py   Diagnóstico, lacunas e simulação
│   ├── assessment_service.py    Aplicação e validação do teste
│   ├── recruitment_service.py   Vagas, ranking e autorização
│   └── auth_service.py
└── api/v1/endpoints/      auth · teams · questionnaires · jobs
```

---

## 🛠️ Comandos Make

| Comando | Descrição |
| :--- | :--- |
| `make dev-local` | Sobe a API sem Docker, com SQLite local |
| `make venv` | Cria `.venv` e instala as dependências |
| `make bootstrap` | Sobe tudo do zero: containers + migrações + seed |
| `make up` / `make down` / `make down-v` | Ciclo de vida dos containers |
| `make migrate` / `make downgrade` | Aplica / reverte migrações |
| `make makemigrations m="nome"` | Gera nova migração |
| `make seed` / `make seed-local` | Questionário padrão (idempotente) |
| `make test` / `make test-local` | Suíte de testes |
| `make ruff-check` / `make ruff-fix` / `make ruff-format` | Lint e formatação |
| `make clean-db` | Apaga o banco SQLite local |
| `make logs` / `make ps` / `make exec-api` / `make exec-db` | Operação |

---

## ⚠️ Limitações conhecidas do MVP

Registradas aqui de propósito — são decisões pendentes, não esquecimentos.
Contexto completo em `docs/visao-de-negocio.md`.

- **O instrumento não é validado psicometricamente.** As cargas dos fatores e os pesos das
  competências são propostas, não coeficientes empíricos. Ver §10.3 do documento de visão.
- **Ipsatividade.** O formato de escolha forçada torna os escores parcialmente relativos dentro
  de cada pessoa, o que complica comparação entre pessoas. Mitigado, não eliminado — detalhes
  em `app/core/big_five.py`.
- **20 cenários é um banco pequeno.** Suficiente para o MVP, insuficiente contra vazamento de
  itens. A rotação de itens prevista em §10.4 do documento de visão não existe.
- **Agregação por média.** A média esconde distribuição: um time com metade das pessoas em 5 e
  metade em 1 tem a mesma média de um time todo em 3. `dispersion` e `members_below_threshold`
  expõem isso, mas a decisão entre média, cobertura ou máximo continua em aberto (§11.2) — e com
  o SJT ela pesa mais, porque a média de perfis ipsativos regride ao centro.
- **Escala normativa, não absoluta.** Nenhum número da API sustenta a afirmação "esta pessoa
  domina a competência X" — apenas "escolhe estas condutas mais/menos que o acaso".
- **Sem trilha de auditoria LGPD.** Consentimento granular, registro de decisão automatizada e
  canal de revisão humana (Art. 20) ainda não implementados.
- **Sem monitoramento de impacto adverso.** A regra dos 4/5 por etapa é requisito do MVP no
  documento de visão e ainda não existe.
- **Etapas 3, 6 e 7 do fluxo original ausentes**: análise de CV/GitHub, micro-resumo por IA e
  análise de entrevista.
- **Google OAuth em modo mock por padrão.** Trocar `GOOGLE_CLIENT_ID` antes de qualquer uso real.
