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
    # Bloco a que o cenário pertence. Só de apresentação: a ordem de resposta
    # continua livre e o cálculo do perfil ignora o agrupamento.
    level: int = 0
    options: list[QuestionOptionResponse]


class LevelResponse(BaseModel):
    """Um bloco de cenários do instrumento.

    Os títulos descrevem o tipo de situação, nunca o traço medido — ver
    `app/core/gamification.py`.
    """

    index: int
    title: str
    subtitle: str
    first_position: int
    question_count: int
    estimated_seconds: int


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
    # Blocos em que os cenários são apresentados, e o tempo que o instrumento
    # inteiro deve levar. O cliente não precisa inventar nem os rótulos nem a
    # estimativa — se o banco de itens crescer, a UI acompanha sozinha.
    levels: list[LevelResponse] = Field(default_factory=list)
    estimated_minutes: int = 0
    questions: list[QuestionResponse]

    @classmethod
    def from_model(cls, questionnaire) -> "QuestionnaireResponse":
        """Monta a resposta declarando o que o instrumento mede.

        `traits`, `derived_dimensions` e `levels` não são colunas — vêm das
        constantes do framework. Expor os três deixa explícito para quem consome
        a API que a nota de soft skill é derivada, não medida diretamente, e que
        o agrupamento em níveis é de apresentação.
        """
        from app.core.big_five import TRAITS
        from app.core.gamification import build_levels, estimated_seconds, level_index_for
        from app.core.soft_skills import DIMENSIONS

        # O nível vem da ordem de exibição, não de `position`: instrumentos
        # editados à mão podem ter posições esparsas, e um buraco na numeração
        # deslocaria os blocos.
        questions = [
            QuestionResponse(
                id=question.id,
                context=question.context,
                text=question.text,
                position=question.position,
                level=level_index_for(ordinal),
                options=[QuestionOptionResponse.model_validate(o) for o in question.options],
            )
            for ordinal, question in enumerate(questionnaire.questions)
        ]

        levels = [
            LevelResponse(
                index=level.index,
                title=level.title,
                subtitle=level.subtitle,
                first_position=level.first_position,
                question_count=level.question_count,
                estimated_seconds=estimated_seconds(level.question_count),
            )
            for level in build_levels(len(questions))
        ]

        return cls(
            id=questionnaire.id,
            title=questionnaire.title,
            description=questionnaire.description,
            is_default=questionnaire.is_default,
            traits=list(TRAITS),
            derived_dimensions=list(DIMENSIONS),
            levels=levels,
            estimated_minutes=round(estimated_seconds(len(questions)) / 60),
            questions=questions,
        )


class SingleAnswerSubmit(BaseModel):
    question_id: UUID
    selected_option_id: UUID
    # Tempo gasto no cenário, medido pelo cliente. Opcional: quem integra pela
    # API (script de demo, testes, carga em lote) não tem essa medida, e exigi-la
    # inventaria número. Ver `app/models/questionnaire.py`.
    elapsed_ms: int | None = Field(default=None, ge=0)


class QuestionnaireSubmitRequest(BaseModel):
    answers: list[SingleAnswerSubmit] = Field(..., min_length=1)


class AssessmentAnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question_id: UUID
    selected_option_id: UUID
    elapsed_ms: int | None = None
    created_at: datetime


class LevelProgressResponse(LevelResponse):
    """Um nível com o que a pessoa já respondeu dentro dele."""

    answered_questions: int
    is_complete: bool


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

    # ---------------------------------------------------------------- jogo
    # Progressão por nível e ritmo. Nada aqui avalia a escolha da pessoa — o
    # instrumento não tem alternativa certa, então o reforço é de avanço, não de
    # acerto (ver `app/core/gamification.py`).
    levels: list[LevelProgressResponse] = Field(default_factory=list)
    # Primeiro nível ainda incompleto — é onde a pessoa retoma. Quando tudo está
    # respondido, aponta para o último.
    current_level: int = 0
    # Soma dos tempos efetivamente medidos. Nulo quando nenhuma resposta trouxe
    # medida (submissão por script), o que é diferente de "levou zero segundo".
    elapsed_seconds: int | None = None
    estimated_seconds_remaining: int = 0


class SubmitAnswersResponse(BaseModel):
    message: str
    questionnaire_id: UUID
    saved_answers: int
    progress: AssessmentProgressResponse
