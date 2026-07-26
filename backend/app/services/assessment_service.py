"""Aplicação do teste situacional (SJT) e cálculo do perfil do respondente.

Mesmo instrumento, dois momentos: os integrantes do time respondem **antes** da
vaga abrir (Etapa 1) e o candidato responde durante o processo (Etapa 5). Manter
a submissão em um único serviço garante que os dois perfis fiquem na mesma régua
— sem isso a comparação time × candidato não significa nada.
"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.gamification import build_levels, estimated_seconds
from app.models.questionnaire import AssessmentAnswer, Question, Questionnaire
from app.repositories.questionnaire_repository import AnswerInput, QuestionnaireRepository
from app.schemas.questionnaire import (
    AssessmentProgressResponse,
    LevelProgressResponse,
    SingleAnswerSubmit,
)
from app.services.scoring import (
    ItemBounds,
    ScoredOption,
    big_five_profile,
    item_bounds,
    soft_skills_from_traits,
)


def bounds_from_questions(questions: list[Question]) -> list[ItemBounds]:
    """Extremos alcançáveis por fator em cada item — base da normalização."""
    return [item_bounds(q.id, [option.loadings_map() for option in q.options]) for q in questions]


def selection_from_answers(answers: list[AssessmentAnswer]) -> list[ScoredOption]:
    return [
        ScoredOption(question_id=answer.question_id, loadings=answer.selected_option.loadings_map())
        for answer in answers
        if answer.selected_option is not None
    ]


def trait_profile_from_answers(answers: list[AssessmentAnswer]) -> dict[str, float]:
    """Perfil Big Five de quem respondeu.

    Os limites de normalização vêm dos próprios itens respondidos, alcançados
    via `answer.question.options` — por isso o repositório carrega essa relação.
    """
    if not answers:
        return {}

    questions = {a.question.id: a.question for a in answers if a.question is not None}
    return big_five_profile(selection_from_answers(answers), bounds_from_questions(list(questions.values())))


def profile_from_answers(answers: list[AssessmentAnswer]) -> dict[str, float]:
    """Soft skills derivadas dos fatores. Base de todo cálculo do produto.

    Assinatura preservada de propósito: diagnóstico do time, análise de lacuna e
    motor de fit continuam consumindo um dict competência → nota 1–5, sem saber
    que a medida passou a vir de um SJT.
    """
    return soft_skills_from_traits(trait_profile_from_answers(answers))


class AssessmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.quest_repo = QuestionnaireRepository(db)

    async def get_questionnaire_or_404(self, questionnaire_id: UUID) -> Questionnaire:
        questionnaire = await self.quest_repo.get_by_id(questionnaire_id)
        if not questionnaire:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Questionnaire with ID {questionnaire_id} not found",
            )
        return questionnaire

    async def get_default_questionnaire_or_404(self) -> Questionnaire:
        questionnaire = await self.quest_repo.get_default()
        if not questionnaire:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Nenhum questionário padrão cadastrado. Rode o seed do banco "
                    "(`make seed` ou `python -m app.db.seed`)."
                ),
            )
        return questionnaire

    async def submit_answers(
        self, user_id: UUID, questionnaire_id: UUID, answers: list[SingleAnswerSubmit]
    ) -> tuple[int, AssessmentProgressResponse]:
        """Grava as escolhas de uma pessoa, validando-as contra o instrumento.

        Sem essa validação seria possível gravar a escolha de um item de outro
        questionário — ou uma alternativa que não pertence ao cenário — e
        contaminar o perfil do time.
        """
        questionnaire = await self.get_questionnaire_or_404(questionnaire_id)

        submitted_ids = [a.question_id for a in answers]
        duplicates = {qid for qid in submitted_ids if submitted_ids.count(qid) > 1}
        if duplicates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicated question_id in payload: {sorted(str(q) for q in duplicates)}",
            )

        questions_by_id = {q.id: q for q in questionnaire.questions}
        unknown = [qid for qid in submitted_ids if qid not in questions_by_id]
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"As questões {sorted(str(q) for q in unknown)} não pertencem ao questionário {questionnaire_id}."
                ),
            )

        for answer in answers:
            valid_options = {o.id for o in questions_by_id[answer.question_id].options}
            if answer.selected_option_id not in valid_options:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(f"A alternativa {answer.selected_option_id} não pertence ao cenário {answer.question_id}."),
                )

        saved = await self.quest_repo.save_answers(
            user_id,
            [
                AnswerInput(
                    question_id=a.question_id,
                    selected_option_id=a.selected_option_id,
                    elapsed_ms=a.elapsed_ms,
                )
                for a in answers
            ],
        )
        progress = await self.get_progress(user_id, questionnaire_id)
        return len(saved), progress

    async def get_progress(self, user_id: UUID, questionnaire_id: UUID) -> AssessmentProgressResponse:
        questionnaire = await self.get_questionnaire_or_404(questionnaire_id)
        answers = await self.quest_repo.get_user_answers_for_questionnaire(user_id, questionnaire_id)

        ordered = list(questionnaire.questions)
        all_ids = {q.id for q in ordered}
        answered_ids = {a.question_id for a in answers}

        traits = trait_profile_from_answers(answers)
        levels = self._level_progress(ordered, answered_ids)

        # Tempo medido: só as respostas que trouxeram medida entram. Somar zero
        # pelas que vieram sem ela produziria um "teste de 4 minutos" falso.
        measured = [a.elapsed_ms for a in answers if a.elapsed_ms is not None]

        return AssessmentProgressResponse(
            questionnaire_id=questionnaire_id,
            user_id=user_id,
            total_questions=len(all_ids),
            answered_questions=len(answered_ids),
            is_complete=bool(all_ids) and all_ids.issubset(answered_ids),
            missing_question_ids=sorted(all_ids - answered_ids, key=str),
            trait_scores=traits,
            dimension_scores=soft_skills_from_traits(traits),
            levels=levels,
            current_level=next((level.index for level in levels if not level.is_complete), max(0, len(levels) - 1)),
            elapsed_seconds=round(sum(measured) / 1000) if measured else None,
            estimated_seconds_remaining=estimated_seconds(len(all_ids) - len(answered_ids & all_ids)),
        )

    @staticmethod
    def _level_progress(ordered: list[Question], answered_ids: set[UUID]) -> list[LevelProgressResponse]:
        """Quanto de cada bloco a pessoa já respondeu.

        O corte é pela **ordem de exibição**, a mesma usada em
        `QuestionnaireResponse.from_model` — caso contrário a UI marcaria como
        concluído um nível diferente do que mostrou.
        """
        progress: list[LevelProgressResponse] = []
        for level in build_levels(len(ordered)):
            block = ordered[level.first_position : level.first_position + level.question_count]
            answered = sum(1 for question in block if question.id in answered_ids)
            progress.append(
                LevelProgressResponse(
                    index=level.index,
                    title=level.title,
                    subtitle=level.subtitle,
                    first_position=level.first_position,
                    question_count=level.question_count,
                    estimated_seconds=estimated_seconds(level.question_count),
                    answered_questions=answered,
                    is_complete=answered == level.question_count,
                )
            )
        return progress

    async def get_answers(self, user_id: UUID, questionnaire_id: UUID) -> list[AssessmentAnswer]:
        await self.get_questionnaire_or_404(questionnaire_id)
        return await self.quest_repo.get_user_answers_for_questionnaire(user_id, questionnaire_id)
