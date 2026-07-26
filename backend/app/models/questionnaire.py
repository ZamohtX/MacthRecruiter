import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.user import User


class Questionnaire(Base):
    __tablename__ = "questionnaires"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Instrumento padrão da plataforma, aplicado ao time e ao candidato quando a
    # vaga não especifica outro. Apenas um questionário deve ter is_default=True.
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Relationships
    questions: Mapped[list["Question"]] = relationship(
        "Question",
        back_populates="questionnaire",
        cascade="all, delete-orphan",
        order_by="Question.position",
    )
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="questionnaire")


class Question(Base):
    """Um item SJT: a situação de trabalho apresentada ao respondente.

    O item não pertence a uma soft skill — quem carrega a medida são as
    alternativas, através das cargas nos fatores Big Five.
    """

    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    questionnaire_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questionnaires.id", ondelete="CASCADE"), nullable=False
    )
    # Rótulo temático do cenário ("Prazo e dívida técnica"). Serve para exibição e
    # para checar cobertura de contextos — não entra no cálculo.
    context: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Ordem de exibição do item no questionário.
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    questionnaire: Mapped["Questionnaire"] = relationship("Questionnaire", back_populates="questions")
    options: Mapped[list["QuestionOption"]] = relationship(
        "QuestionOption",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionOption.position",
    )
    answers: Mapped[list["AssessmentAnswer"]] = relationship(
        "AssessmentAnswer", back_populates="question", cascade="all, delete-orphan"
    )


class QuestionOption(Base):
    """Uma conduta possível diante do cenário, com suas cargas nos fatores.

    Todas as alternativas de um item são condutas profissionalmente defensáveis:
    a diferença entre elas é de ênfase de traço, não de qualidade. Uma alternativa
    obviamente melhor reintroduziria a resposta socialmente desejável que o
    formato SJT existe para evitar.
    """

    __tablename__ = "question_options"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="options")
    loadings: Mapped[list["OptionTraitLoading"]] = relationship(
        "OptionTraitLoading", back_populates="option", cascade="all, delete-orphan"
    )
    answers: Mapped[list["AssessmentAnswer"]] = relationship("AssessmentAnswer", back_populates="selected_option")

    def loadings_map(self) -> dict[str, float]:
        """Cargas como dict fator → peso, formato usado pelo módulo de scoring."""
        return {loading.trait: loading.weight for loading in self.loadings}


class OptionTraitLoading(Base):
    """Peso de uma alternativa em um fator Big Five.

    Tabela relacional em vez de coluna JSON: permite consultar e auditar a chave
    de correção por fator, que é justamente o que um questionamento sobre viés
    ou sobre validade do instrumento vai exigir ver.
    """

    __tablename__ = "option_trait_loadings"
    __table_args__ = (UniqueConstraint("option_id", "trait", name="uq_loading_option_trait"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    option_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("question_options.id", ondelete="CASCADE"), nullable=False)
    trait: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    option: Mapped["QuestionOption"] = relationship("QuestionOption", back_populates="loadings")


class AssessmentAnswer(Base):
    __tablename__ = "assessment_answers"
    # Uma resposta por pessoa por item: reenviar o questionário troca a escolha
    # em vez de acumular respostas e distorcer o perfil.
    __table_args__ = (UniqueConstraint("user_id", "question_id", name="uq_answer_user_question"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    # A resposta é a conduta escolhida, não uma nota. É o que caracteriza o SJT.
    selected_option_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("question_options.id", ondelete="CASCADE"), nullable=False
    )
    # Tempo que a pessoa levou neste cenário, medido pelo cliente.
    #
    # Existe por dois motivos. Primeiro, a duração-alvo de 10–15 min do teste é
    # uma **premissa** que o documento de visão manda validar com dado real
    # (§Etapa 5) — sem medir, ela nunca sai do papel. Segundo, é o insumo para a
    # detecção de resposta apressada prevista em §10.4: quem fecha 20 cenários em
    # 40 segundos não leu nenhum, e o perfil resultante não vale nada.
    #
    # Nulo é esperado: respostas gravadas por script (seed, demo, testes) e as
    # anteriores a esta coluna não têm medida. Só o cliente sabe o tempo real, e
    # por isso ele **não é confiável para punir ninguém** — serve para calibrar e
    # para levantar suspeita, não para eliminar candidato.
    elapsed_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="answers")
    question: Mapped["Question"] = relationship("Question", back_populates="answers")
    selected_option: Mapped["QuestionOption"] = relationship("QuestionOption", back_populates="answers")
