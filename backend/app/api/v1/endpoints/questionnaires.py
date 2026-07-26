"""Aplicação do teste comportamental.

É por aqui que os integrantes do time respondem o diagnóstico **antes** do
processo seletivo — a fundação do produto. O candidato responde o mesmo
instrumento em `/jobs/{job_id}/answers`.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.questionnaire import Questionnaire
from app.models.user import User
from app.schemas.questionnaire import (
    AssessmentAnswerResponse,
    AssessmentProgressResponse,
    QuestionnaireResponse,
    QuestionnaireSubmitRequest,
    QuestionnaireSummaryResponse,
    SubmitAnswersResponse,
)
from app.services.assessment_service import AssessmentService

router = APIRouter()


def _to_summary(questionnaire: Questionnaire) -> QuestionnaireSummaryResponse:
    return QuestionnaireSummaryResponse(
        id=questionnaire.id,
        title=questionnaire.title,
        description=questionnaire.description,
        is_default=questionnaire.is_default,
        question_count=len(questionnaire.questions),
        contexts=sorted({q.context for q in questionnaire.questions}),
    )


@router.get("", response_model=list[QuestionnaireSummaryResponse])
async def list_questionnaires(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista os instrumentos disponíveis."""
    service = AssessmentService(db)
    return [_to_summary(q) for q in await service.quest_repo.list_all()]


@router.get("/default", response_model=QuestionnaireResponse)
async def get_default_questionnaire(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Instrumento SJT padrão, com todos os cenários e alternativas.

    Declarado antes de `/{questionnaire_id}` para que "default" não seja
    interpretado como UUID.
    """
    service = AssessmentService(db)
    return QuestionnaireResponse.from_model(await service.get_default_questionnaire_or_404())


@router.get("/{questionnaire_id}", response_model=QuestionnaireResponse)
async def get_questionnaire(
    questionnaire_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AssessmentService(db)
    return QuestionnaireResponse.from_model(await service.get_questionnaire_or_404(questionnaire_id))


@router.post("/{questionnaire_id}/answers", response_model=SubmitAnswersResponse, status_code=200)
async def submit_answers(
    questionnaire_id: UUID,
    payload: QuestionnaireSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Grava as condutas escolhidas pela pessoa autenticada.

    Aceita envio parcial: o progresso retornado indica o que ainda falta, para
    que o teste possa ser respondido em etapas.
    """
    service = AssessmentService(db)
    saved, progress = await service.submit_answers(current_user.id, questionnaire_id, payload.answers)

    return SubmitAnswersResponse(
        message="Respostas registradas com sucesso.",
        questionnaire_id=questionnaire_id,
        saved_answers=saved,
        progress=progress,
    )


@router.get("/{questionnaire_id}/my-progress", response_model=AssessmentProgressResponse)
async def get_my_progress(
    questionnaire_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Progresso, perfil Big Five e soft skills derivadas da própria pessoa."""
    service = AssessmentService(db)
    return await service.get_progress(current_user.id, questionnaire_id)


@router.get("/{questionnaire_id}/my-answers", response_model=list[AssessmentAnswerResponse])
async def get_my_answers(
    questionnaire_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Escolhas já enviadas pela própria pessoa — permite retomar o teste."""
    service = AssessmentService(db)
    return await service.get_answers(current_user.id, questionnaire_id)
