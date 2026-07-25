from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.questionnaire import AssessmentAnswer, Question, Questionnaire


class QuestionnaireRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, questionnaire_id: UUID) -> Questionnaire | None:
        stmt = (
            select(Questionnaire)
            .options(selectinload(Questionnaire.questions))
            .where(Questionnaire.id == questionnaire_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_questionnaire(
        self, title: str, description: str | None = None
    ) -> Questionnaire:
        q = Questionnaire(title=title, description=description)
        self.db.add(q)
        await self.db.commit()
        await self.db.refresh(q)
        return q

    async def add_question(
        self, questionnaire_id: UUID, dimension: str, text: str
    ) -> Question:
        question = Question(
            questionnaire_id=questionnaire_id, dimension=dimension, text=text
        )
        self.db.add(question)
        await self.db.commit()
        await self.db.refresh(question)
        return question

    async def save_answer(
        self, user_id: UUID, question_id: UUID, score: int
    ) -> AssessmentAnswer:
        # Check if answer exists and update, or insert new
        stmt = select(AssessmentAnswer).where(
            AssessmentAnswer.user_id == user_id,
            AssessmentAnswer.question_id == question_id,
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.score = score
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        answer = AssessmentAnswer(user_id=user_id, question_id=question_id, score=score)
        self.db.add(answer)
        await self.db.commit()
        await self.db.refresh(answer)
        return answer

    async def get_user_answers(self, user_id: UUID) -> list[AssessmentAnswer]:
        stmt = (
            select(AssessmentAnswer)
            .options(selectinload(AssessmentAnswer.question))
            .where(AssessmentAnswer.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_users_answers(self, user_ids: list[UUID]) -> list[AssessmentAnswer]:
        if not user_ids:
            return []
        stmt = (
            select(AssessmentAnswer)
            .options(selectinload(AssessmentAnswer.question))
            .where(AssessmentAnswer.user_id.in_(user_ids))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
