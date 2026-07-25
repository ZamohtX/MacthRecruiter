from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_google_id_token
from app.models.user import UserRole
from app.repositories.job_repository import JobRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import GoogleAuthRequest, TokenResponse, UserResponse


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.team_repo = TeamRepository(db)
        self.job_repo = JobRepository(db)

    async def authenticate_google(self, auth_data: GoogleAuthRequest) -> TokenResponse:
        try:
            google_info = verify_google_id_token(auth_data.id_token)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
            ) from e

        email = google_info.get("email")
        name = google_info.get("name", email.split("@")[0] if email else "User")
        google_id = google_info.get("sub")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google token does not contain a valid email",
            )

        # Find existing user
        user = await self.user_repo.get_by_email(email)

        # Determine target role and links
        invite_team_id: UUID | None = None
        if auth_data.invite_token:
            invite = await self.team_repo.get_invite_token(auth_data.invite_token)
            if invite:
                invite_team_id = invite.team_id

        valid_job_id: UUID | None = None
        if auth_data.job_id:
            job = await self.job_repo.get_by_id(auth_data.job_id)
            if job:
                valid_job_id = job.id

        if not user:
            # Determine initial role
            if invite_team_id:
                initial_role = UserRole.MEMBER
            elif valid_job_id:
                initial_role = UserRole.CANDIDATE
            else:
                initial_role = UserRole.RECRUITER

            user = await self.user_repo.create(
                email=email, name=name, role=initial_role, google_id=google_id
            )
        else:
            if not user.google_id and google_id:
                user.google_id = google_id
                await self.db.commit()

        # Link team membership if invite token present
        if invite_team_id:
            await self.team_repo.add_member(invite_team_id, user.id)
            if user.role == UserRole.CANDIDATE:
                await self.user_repo.update_role(user, UserRole.MEMBER)

        # Link job candidate application if job_id present
        if valid_job_id:
            await self.job_repo.create_application(valid_job_id, user.id)

        access_token = create_access_token(subject=str(user.id))

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )
