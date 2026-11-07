"""Združi vse API poti v en router, ki ga vključi aplikacija."""

from fastapi import APIRouter

from app.api.routes import health

api_router = APIRouter()
api_router.include_router(health.router)
