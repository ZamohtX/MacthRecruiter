from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QuestionOptionResponse(BaseModel):
    """Alternativa exibida ao respondente.

    **As cargas nos fatores não são expostas de propósito.** Se o candidato vir
    que uma alternativa pontua Conscienciosidade, ele escolhe pelo rótulo em vez
    de pela conduta — é a desejabilidade social que o formato SJT existe para
    evitar. A chave de correção fica auditável no banco
    (`option_trait_loadings`), não na resposta da API.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    text: str
    position: int = 0


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    context: str
    text: str
    position: int = 0
    options: list[QuestionOptionResponse]


class QuestionnaireSummaryResponse(BaseModel):
    """Cabeçalho do questionário, sem os itens — para listagens."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None = None
    is_default: bool = False
    question_count: int = 0
    contexts: list[str] = Field(default_factory=list)


class QuestionnaireResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None = None
    is_default: bool = False
    format: str = "SJT"
    # Camada latente medida pelo instrumento e competências derivadas dela.
    traits: list[str] = Field(default_factory=list)
    derived_dimensions: list[str] = Field(default_factory=list)
    questions: list[QuestionResponse]

    @classmethod
    def from_model(cls, questionnaire) -> "QuestionnaireResponse":
        """Monta a resposta declarando o que o instrumento mede.

        `traits` e `derived_dimensions` não são colunas — vêm das constantes do
        framework. Expor os dois deixa explícito para quem consome a API que a
        nota de soft skill é derivada, não medida diretamente.
        """
        from app.core.big_five import TRAITS
        from app.core.soft_skills import DIMENSIONS

        return cls(
            id=questionnaire.id,
            title=questionnaire.title,
            description=questionnaire.description,
            is_default=questionnaire.is_default,
            traits=list(TRAITS),
            derived_dimensions=list(DIMENSIONS),
            questions=[QuestionResponse.model_validate(q) for q in questionnaire.questions],
        )


class SingleAnswerSubmit(BaseModel):
    question_id: UUID
    selected_option_id: UUID


class QuestionnaireSubmitRequest(BaseModel):
    answers: list[SingleAnswerSubmit] = Field(..., min_length=1)


class AssessmentAnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question_id: UUID
    selected_option_id: UUID
    created_at: datetime


class AssessmentProgressResponse(BaseModel):
    """Estado do preenchimento do instrumento por uma pessoa."""

    questionnaire_id: UUID
    user_id: UUID
    total_questions: int
    answered_questions: int
    is_complete: bool
    missing_question_ids: list[UUID] = Field(default_factory=list)
    # Camada latente: os cinco fatores Big Five.
    trait_scores: dict[str, float] = Field(default_factory=dict)
    # Camada observável: as 10 soft skills derivadas dos fatores.
    dimension_scores: dict[str, float] = Field(default_factory=dict)


class SubmitAnswersResponse(BaseModel):
    message: str
    questionnaire_id: UUID
    saved_answers: int
    progress: AssessmentProgressResponse
