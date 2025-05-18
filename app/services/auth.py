from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token
from app.db.session import get_db
from app.integrations.database import Database
from app.models.user import User
from app.schemas.auth import TokenPayload, UserInDB
from app.utils.logging import get_logger

# In app/services/auth.py
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")

logger = get_logger("auth_service")


class AuthService:
    """Service for authentication and user management"""

    def __init__(self, db: Database):
        """
        Initialize auth service
        
        Args:
            db: Database client
        """
        self.db = db
        self.logger = logger

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate user
        
        Args:
            email: User email
            password: User password
            
        Returns:
            User if authentication successful, None otherwise
        """
        try:
            user = await self.db.get_user_by_email(email)
            if not user:
                return None
            if not verify_password(password, user.hashed_password):
                return None
            return user
        except Exception as e:
            self.logger.error(f"Error authenticating user: {str(e)}")
            return None

    async def get_current_user(self, token: str = Depends(oauth2_scheme)) -> User:
        """
        Get current user from token
        
        Args:
            token: JWT token
            
        Returns:
            User
            
        Raises:
            HTTPException: If token is invalid or user not found
        """
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=["HS256"]
            )
            token_data = TokenPayload(**payload)
        except (JWTError, ValidationError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        user = await self.db.get_user_by_email(token_data.sub)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user

    async def get_current_active_user(
        self, current_user: User = Depends(get_current_user)
    ) -> User:
        """
        Get current active user
        
        Args:
            current_user: Current user
            
        Returns:
            User
            
        Raises:
            HTTPException: If user is inactive
        """
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        return current_user

    async def get_current_admin_user(
        self, current_user: User = Depends(get_current_active_user)
    ) -> User:
        """
        Get current admin user
        
        Args:
            current_user: Current user
            
        Returns:
            User
            
        Raises:
            HTTPException: If user is not admin
        """
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """
    Get auth service
    
    Args:
        db: Database session
        
    Returns:
        AuthService
    """
    db_client = Database(db)
    return AuthService(db_client)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """
    Get current user from token
    
    Args:
        token: JWT token
        auth_service: Auth service
        
    Returns:
        User
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=["HS256"]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user = await auth_service.db.get_user_by_email(token_data.sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user
    
    Args:
        current_user: Current user
        
    Returns:
        User
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current admin user
    
    Args:
        current_user: Current user
        
    Returns:
        User
        
    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user