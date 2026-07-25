import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.job import CandidateApplication
    from app.models.questionnaire import AssessmentAnswer
    from app.models.team import Team, TeamMember


class UserRole(str, enum.Enum):
    RECRUITER = "RECRUITER"
    MEMBER = "MEMBER"
    CANDIDATE = "CANDIDATE"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum"), default=UserRole.CANDIDATE, nullable=False
    )
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    team_memberships: Mapped[list["TeamMember"]] = relationship(
        "TeamMember", back_populates="user", cascade="all, delete-orphan"
    )
    owned_teams: Mapped[list["Team"]] = relationship("Team", back_populates="owner")
    answers: Mapped[list["AssessmentAnswer"]] = relationship(
        "AssessmentAnswer", back_populates="user", cascade="all, delete-orphan"
    )
    applications: Mapped[list["CandidateApplication"]] = relationship(
        "CandidateApplication", back_populates="candidate", cascade="all, delete-orphan"
    )
