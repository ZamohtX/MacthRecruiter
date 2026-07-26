from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.integrations.gemini.client import GeminiClient, GeminiError
from app.integrations.gemini.summary import build_prompt, fallback_summary
from app.models.job import ApplicationStatus
from app.models.user import User
from app.repositories.job_repository import JobRepository
from app.schemas.integration import AiSummaryResponse
from app.schemas.job import (
    ApplicationResponse,
    ApplicationStatusUpdate,
    CandidateSummaryResponse,
    ImpactAnalysisResponse,
    JobCreate,
    JobDetailResponse,
    JobResponse,
)
from app.schemas.questionnaire import (
    AssessmentProgressResponse,
    QuestionnaireResponse,
    QuestionnaireSubmitRequest,
    SubmitAnswersResponse,
)
from app.services.assessment_service import AssessmentService
from app.services.recruitment_service import RecruitmentService
from app.services.soft_skills_service import SoftSkillsService

router = APIRouter()

# Cache em processo do resumo por (job, candidato): as respostas do candidato são
# estáveis, então não vale gastar quota do Gemini reescrevendo o mesmo texto a
# cada abertura da tela.
_summary_cache: dict[tuple[UUID, UUID], AiSummaryResponse] = {}


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(
    payload: JobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Abre uma vaga para um time. Sem `questionnaire_id`, usa o instrumento padrão."""
    service = RecruitmentService(db)
    return await service.create_job(
        user=current_user,
        title=payload.title,
        team_id=payload.team_id,
        questionnaire_id=payload.questionnaire_id,
        description=payload.description,
    )


@router.get("", response_model=list[JobResponse])
async def list_my_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vagas dos times de que a pessoa autenticada é responsável."""
    service = RecruitmentService(db)
    return await service.list_jobs_for_user(current_user)


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detalhe da vaga. Visível ao candidato — não expõe dado de outros candidatos."""
    service = RecruitmentService(db)
    return await service.get_job_detail(job_id)


@router.get("/{job_id}/questionnaire", response_model=QuestionnaireResponse)
async def get_job_questionnaire(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Instrumento que o candidato desta vaga deve responder — o mesmo aplicado ao time."""
    recruitment = RecruitmentService(db)
    job = await recruitment.get_job_or_404(job_id)

    assessment = AssessmentService(db)
    return QuestionnaireResponse.from_model(await assessment.get_questionnaire_or_404(job.questionnaire_id))


@router.post("/{job_id}/apply", status_code=201)
async def apply_to_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RecruitmentService(db)
    await service.get_job_or_404(job_id)

    job_repo = JobRepository(db)
    application = await job_repo.create_application(job_id=job_id, candidate_id=current_user.id)
    return {"message": "Applied successfully", "application_id": str(application.id)}


@router.post("/{job_id}/answers", response_model=SubmitAnswersResponse, status_code=200)
async def submit_questionnaire_answers(
    job_id: UUID,
    payload: QuestionnaireSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Etapa 5 — o candidato responde o mesmo teste que o time respondeu.

    A candidatura só passa a `SOFT_SKILLS_COMPLETED` quando todos os itens forem
    respondidos; antes disso o perfil está incompleto e não deve ser comparado.
    """
    recruitment = RecruitmentService(db)
    job = await recruitment.get_job_or_404(job_id)

    assessment = AssessmentService(db)
    saved, progress = await assessment.submit_answers(current_user.id, job.questionnaire_id, payload.answers)

    job_repo = JobRepository(db)
    application = await job_repo.get_application(job_id, current_user.id)
    if application and progress.is_complete and application.status == ApplicationStatus.APPLIED:
        await job_repo.update_application_status(application, ApplicationStatus.SOFT_SKILLS_COMPLETED)

    return SubmitAnswersResponse(
        message="Answers submitted successfully",
        questionnaire_id=job.questionnaire_id,
        saved_answers=saved,
        progress=progress,
    )


@router.get("/{job_id}/my-progress", response_model=AssessmentProgressResponse)
async def get_my_job_progress(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Progresso do próprio candidato no teste desta vaga."""
    recruitment = RecruitmentService(db)
    job = await recruitment.get_job_or_404(job_id)

    assessment = AssessmentService(db)
    return await assessment.get_progress(current_user.id, job.questionnaire_id)


@router.get("/{job_id}/candidates", response_model=list[CandidateSummaryResponse])
async def get_job_candidates(
    job_id: UUID,
    min_fit_score: float | None = Query(
        None, ge=0.0, le=100.0, description="Filtrar candidatos com fit_score maior ou igual ao valor especificado"
    ),
    status_filter: ApplicationStatus | None = Query(
        None, alias="status", description="Filtrar candidatos por status da aplicação"
    ),
    limit: int | None = Query(None, ge=1, description="Número máximo de candidatos a retornar"),
    sort_desc: bool = Query(True, description="Se True, ordena pelos mais compatíveis primeiro"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Painel do recrutador: candidatos ranqueados por fit complementar."""
    service = RecruitmentService(db)
    await service.ensure_job_owner(job_id, current_user)

    return await service.get_job_candidates(
        job_id=job_id, min_fit_score=min_fit_score, status_filter=status_filter, limit=limit, sort_desc=sort_desc
    )


@router.post(
    "/{job_id}/candidates/{candidate_id}/impact-analysis",
    response_model=ImpactAnalysisResponse,
)
async def get_candidate_impact_analysis(
    job_id: UUID,
    candidate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Simulação pós-contratação: o que muda no perfil do time se este candidato entrar."""
    recruitment = RecruitmentService(db)
    await recruitment.ensure_job_owner(job_id, current_user)

    soft_skills_service = SoftSkillsService(db)
    return await soft_skills_service.calculate_impact_analysis(job_id=job_id, candidate_id=candidate_id)


@router.post(
    "/{job_id}/candidates/{candidate_id}/ai-summary",
    response_model=AiSummaryResponse,
)
async def get_candidate_ai_summary(
    job_id: UUID,
    candidate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AiSummaryResponse:
    """Resumo do candidato em linguagem simples (Gemini), com fallback determinístico."""
    recruitment = RecruitmentService(db)
    await recruitment.ensure_job_owner(job_id, current_user)

    cache_key = (job_id, candidate_id)
    if cache_key in _summary_cache:
        return _summary_cache[cache_key]

    impact = await SoftSkillsService(db).calculate_impact_analysis(job_id=job_id, candidate_id=candidate_id)

    # Gemini quando dá; senão, o texto-regra com os mesmos dados. O resumo é apoio
    # — nunca deve derrubar a tela por causa de quota/rede.
    try:
        async with GeminiClient.from_settings() as gemini:
            text = await gemini.generate(build_prompt(impact))
        result = AiSummaryResponse(summary=text, source="ai", model=gemini.model)
    except GeminiError:
        result = AiSummaryResponse(summary=fallback_summary(impact), source="fallback")

    _summary_cache[cache_key] = result
    return result


@router.patch(
    "/{job_id}/candidates/{candidate_id}/status",
    response_model=ApplicationResponse,
)
async def update_candidate_status(
    job_id: UUID,
    candidate_id: UUID,
    payload: ApplicationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Move a candidatura no funil (UNDER_REVIEW, REJECTED, HIRED...)."""
    service = RecruitmentService(db)
    await service.ensure_job_owner(job_id, current_user)
    return await service.update_application_status(job_id, candidate_id, payload.status)


@router.post("/{job_id}/candidates/{candidate_id}/hire", response_model=ApplicationResponse)
async def hire_candidate(
    job_id: UUID,
    candidate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Efetiva a contratação: marca como HIRED e adiciona a pessoa ao time.

    A partir daí o candidato passa a compor o perfil do time — a simulação vira
    o diagnóstico real e o ciclo recomeça na próxima vaga.
    """
    service = RecruitmentService(db)
    job = await service.ensure_job_owner(job_id, current_user)

    application = await service.update_application_status(job_id, candidate_id, ApplicationStatus.HIRED)
    await service.team_repo.add_member(job.team_id, candidate_id)

    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Exclui a vaga (e, em cascata, suas candidaturas)."""
    service = RecruitmentService(db)
    await service.ensure_job_owner(job_id, current_user)
    await JobRepository(db).delete_job(job_id)


@router.delete("/{job_id}/candidates/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_candidate(
    job_id: UUID,
    candidate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove uma candidatura da vaga. As respostas da pessoa ficam com ela."""
    service = RecruitmentService(db)
    await service.ensure_job_owner(job_id, current_user)
    removed = await JobRepository(db).delete_application(job_id, candidate_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidatura não encontrada.")
