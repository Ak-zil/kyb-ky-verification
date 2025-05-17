from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.apikey import (
    APIKey, APIKeyCreate, APIKeyUpdate, APIKeySuccess, APIKeyListResponse
)
from app.services.apikey import APIKeyService, get_api_key_service
from app.services.auth import AuthService, get_auth_service, get_current_admin_user

router = APIRouter()


@router.get("/apikeys", response_model=List[APIKey])
async def get_apikeys(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    api_key_service: APIKeyService = Depends(get_api_key_service)
) -> Any:
    """
    Get all API keys
    """
    api_keys = await api_key_service.get_api_keys(skip=skip, limit=limit)
    return api_keys


@router.post("/apikeys", response_model=APIKey)
async def create_apikey(
    apikey_in: APIKeyCreate,
    current_user: User = Depends(get_current_admin_user),
    api_key_service: APIKeyService = Depends(get_api_key_service)
) -> Any:
    """
    Create new API key
    """
    api_key = await api_key_service.create_api_key(apikey_in, current_user.id)
    return api_key


@router.put("/apikeys/{key_id}", response_model=APIKey)
async def update_apikey(
    key_id: int,
    apikey_in: APIKeyUpdate,
    current_user: User = Depends(get_current_admin_user),
    api_key_service: APIKeyService = Depends(get_api_key_service)
) -> Any:
    """
    Update API key
    """
    api_key = await api_key_service.update_api_key(key_id, apikey_in)
    return api_key


@router.delete("/apikeys/{key_id}", response_model=APIKeySuccess)
async def delete_apikey(
    key_id: int,
    current_user: User = Depends(get_current_admin_user),
    api_key_service: APIKeyService = Depends(get_api_key_service)
) -> Any:
    """
    Delete API key
    """
    await api_key_service.delete_api_key(key_id)
    return {"success": True}