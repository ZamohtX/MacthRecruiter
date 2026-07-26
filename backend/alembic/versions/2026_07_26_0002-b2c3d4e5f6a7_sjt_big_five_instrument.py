"""instrumento SJT ancorado em Big Five

Troca o questionário de autoavaliação Likert (item + nota 1–5) por teste de
julgamento situacional (cenário + alternativas com carga nos fatores Big Five).

⚠️ **Esta migração descarta as respostas já coletadas.** Uma nota Likert não tem
conversão para uma escolha de conduta em SJT — não existe alternativa à qual
apontar. Times que já responderam precisam refazer o diagnóstico. Cenários,
alternativas e cargas são recriados pelo seed (`make seed`).

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-26
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # As respostas antigas são incompatíveis com o novo formato (ver docstring).
    op.execute("DELETE FROM assessment_answers")

    op.create_table(
        "question_options",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "option_trait_loadings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("option_id", sa.Uuid(), nullable=False),
        sa.Column("trait", sa.String(length=100), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["option_id"], ["question_options.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("option_id", "trait", name="uq_loading_option_trait"),
    )
    op.create_index(op.f("ix_option_trait_loadings_trait"), "option_trait_loadings", ["trait"], unique=False)

    # O item deixa de pertencer a uma soft skill: quem carrega a medida são as
    # alternativas. `context` passa a ser só o rótulo temático do cenário.
    op.drop_index(op.f("ix_questions_dimension"), table_name="questions")
    op.alter_column("questions", "dimension", new_column_name="context")
    op.create_index(op.f("ix_questions_context"), "questions", ["context"], unique=False)

    # A resposta passa a ser a conduta escolhida, não uma nota.
    op.drop_column("assessment_answers", "score")
    op.add_column("assessment_answers", sa.Column("selected_option_id", sa.Uuid(), nullable=False))
    op.create_foreign_key(
        "fk_assessment_answers_selected_option",
        "assessment_answers",
        "question_options",
        ["selected_option_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Os cenários SJT substituem os itens Likert; o seed recria tudo.
    op.execute("DELETE FROM questions")


def downgrade() -> None:
    op.execute("DELETE FROM assessment_answers")
    op.execute("DELETE FROM questions")

    op.drop_constraint("fk_assessment_answers_selected_option", "assessment_answers", type_="foreignkey")
    op.drop_column("assessment_answers", "selected_option_id")
    op.add_column("assessment_answers", sa.Column("score", sa.Integer(), nullable=False))

    op.drop_index(op.f("ix_questions_context"), table_name="questions")
    op.alter_column("questions", "context", new_column_name="dimension")
    op.create_index(op.f("ix_questions_dimension"), "questions", ["dimension"], unique=False)

    op.drop_index(op.f("ix_option_trait_loadings_trait"), table_name="option_trait_loadings")
    op.drop_table("option_trait_loadings")
    op.drop_table("question_options")
