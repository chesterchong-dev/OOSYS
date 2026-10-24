"""Versioned business API composition root."""
from fastapi import APIRouter

router = APIRouter()

from app.identity.routes import router as identity_router
from app.inventory.routes import router as inventory_router
from app.warehouse.routes import router as warehouse_router

router.include_router(identity_router)
router.include_router(inventory_router)
router.include_router(warehouse_router)
