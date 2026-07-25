import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.questionnaire import Questionnaire
    from app.models.team import Team
    from app.models.user import User


class ApplicationStatus(str, enum.Enum):
    APPLIED = "APPLIED"
    SOFT_SKILLS_COMPLETED = "SOFT_SKILLS_COMPLETED"
    UNDER_REVIEW = "UNDER_REVIEW"
    REJECTED = "REJECTED"
    HIRED = "HIRED"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    questionnaire_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questionnaires.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    # Relationships
    team: Mapped["Team"] = relationship("Team", back_populates="jobs")
    questionnaire: Mapped["Questionnaire"] = relationship("Questionnaire", back_populates="jobs")
    applications: Mapped[list["CandidateApplication"]] = relationship("CandidateApplication", back_populates="job", cascade="all, delete-orphan")


class CandidateApplication(Base):
    __tablename__ = "candidate_applications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status_enum"),
        default=ApplicationStatus.APPLIED,
        nullable=False
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="applications")
    candidate: Mapped["User"] = relationship("User", back_populates="applications")
