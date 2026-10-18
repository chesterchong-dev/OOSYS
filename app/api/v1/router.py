"""Versioned business API composition root."""
from fastapi import APIRouter

router = APIRouter()
# Feature routers are registered here by their owning modules in later phases.
