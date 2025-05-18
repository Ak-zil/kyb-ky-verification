from fastapi import APIRouter

from app.api.admin.router import router as admin_router

router = APIRouter()
router.include_router(admin_router, tags=["admin"])