from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.security import create_api_key
from app.db.session import get_db
from app.integrations.database import Database
from app.schemas.apikey import APIKey, APIKeyCreate, APIKeyUpdate
from app.utils.logging import get_logger

logger = get_logger("apikey_service")


class APIKeyService:
    """Service for API key management"""

    def __init__(self, db: Database):
        """
        Initialize API key service
        
        Args:
            db: Database client
        """
        self.db = db
        self.logger = logger

    async def create_api_key(self, data: APIKeyCreate, user_id: int) -> APIKey:
        """
        Create a new API key
        
        Args:
            data: API key data
            user_id: ID of the user creating the API key
            
        Returns:
            Created API key
        """
        try:
            # Generate API key
            key_value = create_api_key()
            
            # Create API key in database
            api_key_data = {
                "key_value": key_value,
                "name": data.name,
                "client_id": data.client_id,
                "is_active": data.is_active,
                "expires_at": data.expires_at,
                "user_id": user_id
            }

            if api_key_data["expires_at"] and api_key_data["expires_at"].tzinfo:
                api_key_data["expires_at"] = api_key_data["expires_at"].replace(tzinfo=None)

            api_key = await self.db.create_api_key(api_key_data)
            
            return api_key
        except Exception as e:
            self.logger.error(f"Error creating API key: {str(e)}")
            raise

    async def get_api_keys(self, skip: int = 0, limit: int = 100) -> List[APIKey]:
        """
        Get all API keys
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of API keys
        """
        try:
            return await self.db.get_api_keys(skip=skip, limit=limit)
        except Exception as e:
            self.logger.error(f"Error getting API keys: {str(e)}")
            raise

    async def get_api_key(self, api_key_id: int) -> Optional[APIKey]:
        """
        Get API key by ID
        
        Args:
            api_key_id: API key ID
            
        Returns:
            API key if found, None otherwise
        """
        try:
            # Get API key
            result = await self.db.get_api_key(api_key_id)
            if not result:
                raise NotFoundError(f"API key with ID {api_key_id} not found")
            
            return result
        except Exception as e:
            self.logger.error(f"Error getting API key: {str(e)}")
            raise

    async def update_api_key(self, api_key_id: int, data: APIKeyUpdate) -> APIKey:
        """
        Update API key
        
        Args:
            api_key_id: API key ID
            data: Updated API key data
            
        Returns:
            Updated API key
        """
        try:
            # Create update data dictionary with only provided fields
            update_data = data.dict(exclude_unset=True)
            
            # Update API key
            api_key = await self.db.update_api_key(api_key_id, update_data)
            if not api_key:
                raise NotFoundError(f"API key with ID {api_key_id} not found")
            
            return api_key
        except Exception as e:
            self.logger.error(f"Error updating API key: {str(e)}")
            raise

    async def delete_api_key(self, api_key_id: int) -> bool:
        """
        Delete API key
        
        Args:
            api_key_id: API key ID
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            # Delete API key
            result = await self.db.delete_api_key(api_key_id)
            if not result:
                raise NotFoundError(f"API key with ID {api_key_id} not found")
            
            return result
        except Exception as e:
            self.logger.error(f"Error deleting API key: {str(e)}")
            raise

    async def validate_api_key(self, api_key: str) -> bool:
        """
        Validate API key
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Get API key
            api_key_obj = await self.db.get_api_key_by_key_value(api_key)
            if not api_key_obj:
                return False
            
            # Check if API key is active
            if not api_key_obj.is_active:
                return False
            
            # Check if API key is expired
            if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error validating API key: {str(e)}")
            return False


async def get_api_key_service(db: AsyncSession = Depends(get_db)) -> APIKeyService:
    """
    Get API key service
    
    Args:
        db: Database session
        
    Returns:
        APIKeyService
    """
    db_client = Database(db)
    return APIKeyService(db_client)


async def get_api_key(
    api_key: str = Header(..., description="API Key"),
    api_key_service: APIKeyService = Depends(get_api_key_service)
) -> str:
    """
    Dependency for validating API key
    
    Args:
        api_key: API key from header
        api_key_service: API key service
        
    Returns:
        Validated API key
        
    Raises:
        HTTPException: If API key is invalid
    """
    if await api_key_service.validate_api_key(api_key):
        return api_key
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )