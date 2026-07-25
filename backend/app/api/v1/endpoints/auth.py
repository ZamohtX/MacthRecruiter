from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import GoogleAuthRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/google", response_model=TokenResponse, status_code=200)
async def login_google(payload: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):

    auth_service = AuthService(db)
    return await auth_service.authenticate_google(payload)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):

    return current_user
