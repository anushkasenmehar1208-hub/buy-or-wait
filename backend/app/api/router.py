"""Aggregated API router."""
from fastapi import APIRouter

from app.api.routes import account, affordability, auth, profile

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(account.router)
api_router.include_router(profile.router)
api_router.include_router(affordability.router)
