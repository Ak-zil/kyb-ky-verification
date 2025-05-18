from fastapi import APIRouter

from app.api.verify.router import router as verify_router

router = APIRouter()
router.include_router(verify_router, tags=["verification"])