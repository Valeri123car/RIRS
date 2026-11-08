"""Združi vse API poti v en router, ki ga vključi aplikacija."""

from fastapi import APIRouter

from app.api.routes import auth, health, riot_accounts

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(riot_accounts.router)
