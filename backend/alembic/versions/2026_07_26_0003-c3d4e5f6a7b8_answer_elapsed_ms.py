"""tempo de resposta por cenário

Grava quanto tempo a pessoa levou em cada cenário do teste situacional.

Serve para validar com dado real a duração-alvo de 10–15 min, que hoje é
premissa (§Etapa 5 do documento de visão), e é o insumo da detecção de resposta
apressada prevista em §10.4.

Coluna anulável de propósito: respostas gravadas por script (seed, demo, testes)
e todas as anteriores a esta migração não têm medida, e forçar um default
numérico inventaria tempo que ninguém observou.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-26
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("assessment_answers", sa.Column("elapsed_ms", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("assessment_answers", "elapsed_ms")
