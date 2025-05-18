from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.verify import router as verify_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth")
api_router.include_router(admin_router, prefix="/admin")
api_router.include_router(verify_router, prefix="/verify")