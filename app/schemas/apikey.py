from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from pydantic import BaseModel, Field


# API Key Schemas
class APIKeyBase(BaseModel):
    name: str
    client_id: str
    is_active: Optional[bool] = True
    expires_at: Optional[datetime] = None


class APIKeyCreate(APIKeyBase):
    pass


class APIKeyUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class APIKeyInDBBase(APIKeyBase):
    id: int
    key_value: str
    created_at: datetime

    class Config:
        orm_mode = True


class APIKey(APIKeyInDBBase):
    pass


class APIKeyResponse(APIKeyInDBBase):
    pass


class APIKeyListResponse(BaseModel):
    items: List[APIKey]
    total: int


class APIKeySuccess(BaseModel):
    success: bool = True