from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from pydantic import BaseModel, EmailStr, Field, validator


# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None


class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_admin: Optional[bool] = False


class UserCreate(UserBase):
    email: EmailStr
    password: str


class UserUpdate(UserBase):
    password: Optional[str] = None


class UserInDBBase(UserBase):
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class User(UserInDBBase):
    pass


class UserInDB(UserInDBBase):
    hashed_password: str


# Login Request Schema
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# Refresh Token Schema
class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LoginResponse(Token):
    pass


class RefreshTokenResponse(Token):
    pass