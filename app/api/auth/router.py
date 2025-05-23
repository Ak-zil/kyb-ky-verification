from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest, LoginResponse, RefreshTokenRequest, RefreshTokenResponse,
    UserResponse
)
from app.services.auth import AuthService, get_auth_service, get_current_active_user

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = await auth_service.authenticate_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        user.email, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/token", response_model=LoginResponse)
async def login_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service)
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        user.email, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    refresh_token_data: RefreshTokenRequest,
) -> Any:
    """
    Refresh token endpoint
    
    Note: In a production environment, this would validate the refresh token
    and issue a new access token. For simplicity, this implementation just
    issues a new access token without validation.
    """
    try:
        # In a real implementation, validate the refresh token
        # For this example, just issue a new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            "user@example.com", expires_delta=access_token_expires
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

# New endpoints for user info and token verification

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get current user information
    
    This endpoint returns information about the currently authenticated user.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "is_admin": current_user.is_admin,
        "is_active": current_user.is_active
    }

@router.get("/verify-token")
async def verify_auth_token(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Verify authentication token
    
    This endpoint verifies if the provided authentication token is valid.
    """
    return {"valid": True}