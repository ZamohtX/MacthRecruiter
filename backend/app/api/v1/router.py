from fastapi import APIRouter

from app.api.v1.endpoints import auth, jobs, teams

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(teams.router, prefix="/teams", tags=["Teams"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
