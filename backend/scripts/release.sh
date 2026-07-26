#!/bin/sh
# Tarefas de release: rodam uma vez por deploy, antes do tráfego chegar na nova
# revisão. Ficam fora da subida da API porque o Cloud Run sobe várias
# instâncias em paralelo — migração e seed concorrentes brigariam entre si.
#
# Usado como comando do Cloud Run Job (ver docs/deploy-gcp.md).
set -eu

echo "==> Aplicando migrações"
alembic upgrade head

echo "==> Sincronizando o questionário padrão"
python -m app.db.seed

echo "==> Release concluído"
