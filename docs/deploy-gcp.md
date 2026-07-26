# Deploy no Google Cloud

Arquitetura:

| Componente | Serviço |
|---|---|
| API FastAPI | Cloud Run (`matchrecruiter-api`) |
| Banco | Cloud SQL for PostgreSQL 16 |
| Migrações + seed | Cloud Run Job (`matchrecruiter-release`) |
| Frontend React | Firebase Hosting |
| Segredos | Secret Manager |
| Build | Cloud Build + Artifact Registry |

O provisionamento (passos 1–5) roda uma vez. Depois disso, cada deploy é o
passo 6 para o backend e o passo 8 para o frontend.

## Ambiente em produção

Provisionado em 26/07/2026, região `southamerica-east1`:

| | |
| :--- | :--- |
| Projeto | `matchrecruiter` (org `leesin16cami-org`) |
| Frontend | https://matchrecruiter.web.app |
| API | https://matchrecruiter-api-nzucood3mq-rj.a.run.app |
| Cloud SQL | `matchrecruiter:southamerica-east1:matchrecruiter-db` (`db-f1-micro`) |
| Segredos | `matchrecruiter-database-url`, `matchrecruiter-jwt-secret` |
| Imagens | `southamerica-east1-docker.pkg.dev/matchrecruiter/matchrecruiter/api` |

---

## 0. Pré-requisitos

```bash
gcloud auth login
gcloud config set project SEU_PROJETO_ID

export PROJECT_ID=$(gcloud config get-value project)
export REGION=southamerica-east1   # São Paulo

gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  firebase.googleapis.com \
  firebasehosting.googleapis.com
```

## 1. Artifact Registry

```bash
gcloud artifacts repositories create matchrecruiter \
  --repository-format=docker \
  --location=$REGION
```

## 2. Cloud SQL

`db-f1-micro` dá conta do MVP. É o item mais caro da conta — se o objetivo for
só uma demo, um Postgres gerenciado com free tier (Neon, Supabase) substitui
este passo sem mudar nada no código: basta a `DATABASE_URL` do passo 3.

```bash
gcloud sql instances create matchrecruiter-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=$REGION \
  --storage-size=10GB \
  --storage-auto-increase

gcloud sql databases create matchrecruiter --instance=matchrecruiter-db

# Hex, não base64: a senha vai dentro de uma URL, e "+" "/" "=" quebrariam
# o parser da connection string.
export DB_PASSWORD=$(openssl rand -hex 24)
gcloud sql users create matchuser \
  --instance=matchrecruiter-db \
  --password="$DB_PASSWORD"

export INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe matchrecruiter-db \
  --format='value(connectionName)')
echo "$INSTANCE_CONNECTION_NAME"   # projeto:regiao:matchrecruiter-db
```

## 3. Secret Manager

A senha do banco não aparece em variável de ambiente do serviço: a
`DATABASE_URL` inteira vira um segredo.

O `?host=/cloudsql/...` é o formato de socket Unix — é assim que o asyncpg fala
com o Cloud SQL a partir do Cloud Run, sem abrir o banco para a internet.

```bash
printf 'postgresql+asyncpg://matchuser:%s@/matchrecruiter?host=/cloudsql/%s' \
  "$DB_PASSWORD" "$INSTANCE_CONNECTION_NAME" \
  | gcloud secrets create matchrecruiter-database-url --data-file=-

openssl rand -hex 32 \
  | gcloud secrets create matchrecruiter-jwt-secret --data-file=-
```

### IAM

A service account padrão do Compute é quem executa **as duas coisas**: o build
no Cloud Build e o contêiner no Cloud Run. Se a organização tiver a política
`iam.automaticIamGrantsForDefaultServiceAccounts` ativa, ela nasce sem
permissão nenhuma e todo o resto falha — a começar por um 403 de
`storage.objects.get` ao enviar o código-fonte.

```bash
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
export SA="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

# Leitura dos segredos: por segredo, não no projeto inteiro.
for SECRET in matchrecruiter-database-url matchrecruiter-jwt-secret; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:$SA" \
    --role="roles/secretmanager.secretAccessor"
done

# cloudsql.client: conectar no banco. builds.builder: enviar código, escrever
# no Artifact Registry e logar. run.admin + serviceAccountUser: criar revisões.
for ROLE in roles/cloudsql.client roles/cloudbuild.builds.builder \
            roles/run.admin roles/iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA" --role="$ROLE"
done
```

Verifique quais políticas a sua organização impõe antes de debugar 403 no
escuro:

```bash
gcloud organizations list
gcloud resource-manager org-policies list --organization=SEU_ORG_ID
```

## 4. Google OAuth

No [console de credenciais](https://console.cloud.google.com/apis/credentials),
crie um **OAuth 2.0 Client ID** do tipo *Web application*. Guarde o client ID —
ele vai no backend (validação do token) e no frontend (botão de login).

Em produção o modo simulado é desligado: `ENVIRONMENT=production` faz
`_mock_login_allowed()` retornar `False` sempre, então tokens
`mock_google_token_*` deixam de ser aceitos.

As **Authorized JavaScript origins** só podem ser preenchidas depois do passo 8
(quando existe a URL do Hosting). Volte aqui no fim.

## 5. Frontend: habilitar o Firebase e descobrir a URL

Backend e frontend dependem um do outro (CORS de um lado, `VITE_API_BASE_URL`
do outro). O ciclo se quebra descobrindo o domínio do Hosting antes de
qualquer build — não é preciso publicar nada ainda.

```bash
npm install -g firebase-tools
firebase login

firebase projects:addfirebase $PROJECT_ID
firebase hosting:sites:list --project $PROJECT_ID
```

O `firebase.json` já está versionado em `frontend/` — **não rode
`firebase init hosting`**, ele sobrescreveria os rewrites de SPA.

> `addfirebase` retornando 403 logo depois de habilitar as APIs é propagação,
> não permissão: espere 2–3 minutos e repita. Se persistir, aceite os Termos
> do Firebase uma vez em console.firebase.google.com.

Anote a URL (`https://SEU_PROJETO.web.app`) — ela é o `_CORS_ORIGINS` do
passo 6 e a origem autorizada do passo 4.

## 6. Backend: deploy

```bash
cd backend

gcloud builds submit --config cloudbuild.yaml \
  --substitutions=\
_REGION=$REGION,\
_INSTANCE_CONNECTION_NAME=$INSTANCE_CONNECTION_NAME,\
_CORS_ORIGINS='["https://SEU_PROJETO.web.app"]',\
_GOOGLE_CLIENT_ID=SEU_CLIENT_ID.apps.googleusercontent.com
```

O pipeline: constrói a imagem → roda o job de release (migrações + seed) →
publica a revisão nova. Se a migração falhar, o build para e a revisão antiga
continua servindo.

Pegue a URL da API:

```bash
export API_URL=$(gcloud run services describe matchrecruiter-api \
  --region=$REGION --format='value(status.url)')
curl "$API_URL/health"
```

## 7. Frontend: build apontando para a API

`VITE_API_BASE_URL` é embutido **no momento do build**, não lido em runtime —
por isso o build refeito aqui, agora que a URL da API existe.

```bash
cd frontend
VITE_API_BASE_URL=$API_URL \
VITE_GOOGLE_CLIENT_ID=SEU_CLIENT_ID.apps.googleusercontent.com \
npm run build

firebase deploy --only hosting
```

## 8. Fechar o OAuth

Volte ao console de credenciais e adicione em **Authorized JavaScript origins**:

```
https://SEU_PROJETO.web.app
```

---

## Deploys seguintes

```bash
# backend
cd backend && gcloud builds submit --config cloudbuild.yaml --substitutions=...

# frontend
cd frontend && VITE_API_BASE_URL=$API_URL npm run build && firebase deploy --only hosting
```

## Operação

```bash
# logs da API
gcloud run services logs tail matchrecruiter-api --region=$REGION

# rodar migrações sem novo deploy
gcloud run jobs execute matchrecruiter-release --region=$REGION --wait

# console psql
gcloud sql connect matchrecruiter-db --user=matchuser --database=matchrecruiter

# voltar para a revisão anterior
gcloud run services update-traffic matchrecruiter-api --region=$REGION --to-revisions=REVISAO=100
```

## Notas

- **Cold start**: com `--min-instances=0` a primeira requisição depois de um
  período parado leva alguns segundos. `--min-instances=1` elimina isso e passa
  a cobrar a instância parada.
- **Pool de conexões**: cada instância segura `DB_POOL_SIZE` (5) conexões. Com
  `--max-instances=4` são 20 no pico, dentro do limite do `db-f1-micro`. Se
  aumentar as instâncias, revise os dois números juntos.
- **`AUTO_SEED=false` em produção**: o seed é do job de release. Ligado no
  serviço, cada instância nova o executaria em paralelo a cada escala.
- **Sourcemaps**: `vite.config.ts` gera sourcemap no build, o que expõe o
  código-fonte legível em produção. Se não quiser, mude `build.sourcemap` para
  `false`.
- **`/docs` e `/redoc`** ficam públicos. Para fechar, passe `docs_url=None` em
  `app/main.py` quando `settings.is_production`.
