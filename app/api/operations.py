"""Operational endpoints independent of business API versioning."""
from fastapi import APIRouter

router = APIRouter(tags=["Operations"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Basic liveness only; this does not verify database readiness."""
    return {"status": "ok"}
