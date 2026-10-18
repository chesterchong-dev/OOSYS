"""Versioned business API composition root."""
from fastapi import APIRouter

router = APIRouter()

from app.identity.routes import router as identity_router

router.include_router(identity_router)
