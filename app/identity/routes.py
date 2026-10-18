"""Identity module route composition; submodules own their HTTP contracts."""
from fastapi import APIRouter
from app.identity.auth_routes import router as auth_router
from app.identity.session_routes import router as session_router
from app.identity.user_routes import router as user_router
from app.identity.organization_routes import router as organization_router
from app.identity.access_routes import router as access_router
from app.identity.hierarchy_routes import router as hierarchy_router
from app.identity.recovery_routes import router as recovery_router

router = APIRouter(tags=["Identity & Access"])
router.include_router(auth_router)
router.include_router(session_router)
router.include_router(user_router)
router.include_router(organization_router)
router.include_router(access_router)
router.include_router(hierarchy_router)
router.include_router(recovery_router)
