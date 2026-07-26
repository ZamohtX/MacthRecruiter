from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.questionnaire import (
    AssessmentAnswer,
    Question,
    Questionnaire,
    QuestionOption,
)


@dataclass(frozen=True)
class AnswerInput:
    """Uma escolha a gravar, já validada contra o instrumento pelo serviço."""

    question_id: UUID
    selected_option_id: UUID
    elapsed_ms: int | None = None


# Carrega o instrumento inteiro — itens, alternativas e cargas nos fatores.
# Sem as cargas não é possível pontuar uma resposta, e lazy loading em sessão
# async estoura, então o eager load é obrigatório e não uma otimização.
_FULL_QUESTIONNAIRE = (
    selectinload(Questionnaire.questions).selectinload(Question.options).selectinload(QuestionOption.loadings)
)

# Idem para respostas: a alternativa escolhida só vale com suas cargas.
_ANSWER_WITH_LOADINGS = (
    selectinload(AssessmentAnswer.question).selectinload(Question.options).selectinload(QuestionOption.loadings),
    selectinload(AssessmentAnswer.selected_option).selectinload(QuestionOption.loadings),
)


class QuestionnaireRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, questionnaire_id: UUID) -> Questionnaire | None:
        stmt = select(Questionnaire).options(_FULL_QUESTIONNAIRE).where(Questionnaire.id == questionnaire_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Questionnaire]:
        stmt = select(Questionnaire).options(_FULL_QUESTIONNAIRE).order_by(Questionnaire.title)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_default(self) -> Questionnaire | None:
        stmt = select(Questionnaire).options(_FULL_QUESTIONNAIRE).where(Questionnaire.is_default.is_(True))
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_questionnaire(
        self, title: str, description: str | None = None, is_default: bool = False
    ) -> Questionnaire:
        q = Questionnaire(title=title, description=description, is_default=is_default)
        self.db.add(q)
        await self.db.commit()
        await self.db.refresh(q)
        return q

    async def get_questions(self, questionnaire_id: UUID) -> list[Question]:
        stmt = (
            select(Question)
            .options(selectinload(Question.options).selectinload(QuestionOption.loadings))
            .where(Question.questionnaire_id == questionnaire_id)
            .order_by(Question.position, Question.id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_options_by_ids(self, option_ids: list[UUID]) -> list[QuestionOption]:
        if not option_ids:
            return []
        stmt = (
            select(QuestionOption)
            .options(selectinload(QuestionOption.loadings))
            .where(QuestionOption.id.in_(option_ids))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def save_answers(self, user_id: UUID, answers: list[AnswerInput]) -> list[AssessmentAnswer]:
        """Insere ou atualiza várias escolhas em uma única transação.

        Uma submissão parcialmente gravada deixaria o perfil do respondente
        inconsistente, então tudo entra ou nada entra.
        """
        if not answers:
            return []

        stmt = select(AssessmentAnswer).where(
            AssessmentAnswer.user_id == user_id,
            AssessmentAnswer.question_id.in_([a.question_id for a in answers]),
        )
        result = await self.db.execute(stmt)
        existing = {a.question_id: a for a in result.scalars().all()}

        saved: list[AssessmentAnswer] = []
        for incoming in answers:
            answer = existing.get(incoming.question_id)
            if answer is None:
                answer = AssessmentAnswer(
                    user_id=user_id,
                    question_id=incoming.question_id,
                    selected_option_id=incoming.selected_option_id,
                    elapsed_ms=incoming.elapsed_ms,
                )
                self.db.add(answer)
            else:
                answer.selected_option_id = incoming.selected_option_id
                # Vale a **primeira** medida. Revisar uma escolha já lida leva
                # segundos, e sobrescrever encurtaria artificialmente a duração
                # do teste — justamente o número que esta coluna existe para
                # medir.
                if answer.elapsed_ms is None:
                    answer.elapsed_ms = incoming.elapsed_ms
            saved.append(answer)

        await self.db.commit()
        return saved

    async def get_user_answers(self, user_id: UUID) -> list[AssessmentAnswer]:
        stmt = select(AssessmentAnswer).options(*_ANSWER_WITH_LOADINGS).where(AssessmentAnswer.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_users_answers(self, user_ids: list[UUID]) -> list[AssessmentAnswer]:
        if not user_ids:
            return []
        stmt = select(AssessmentAnswer).options(*_ANSWER_WITH_LOADINGS).where(AssessmentAnswer.user_id.in_(user_ids))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_user_answers_for_questionnaire(self, user_id: UUID, questionnaire_id: UUID) -> list[AssessmentAnswer]:
        stmt = (
            select(AssessmentAnswer)
            .options(*_ANSWER_WITH_LOADINGS)
            .join(Question, Question.id == AssessmentAnswer.question_id)
            .where(
                AssessmentAnswer.user_id == user_id,
                Question.questionnaire_id == questionnaire_id,
            )
            .order_by(Question.position)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
