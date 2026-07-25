from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dimension: str
    text: str


class QuestionnaireResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None = None
    questions: list[QuestionResponse]


class SingleAnswerSubmit(BaseModel):
    question_id: UUID
    score: int = Field(..., ge=1, le=5)


class QuestionnaireSubmitRequest(BaseModel):
    answers: list[SingleAnswerSubmit]


class AssessmentAnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question_id: UUID
    score: int
    created_at: datetime
