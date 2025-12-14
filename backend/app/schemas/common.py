"""Common Schemas - General response, pagination, etc."""
from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

T = TypeVar('T')

class ResponseBase(BaseModel):
    """Base response model"""
    success: bool = Field(default=True, description="Request success")
    message: str = Field(default="Success", description="Response message")

class Response(ResponseBase, Generic[T]):
    """Generic response model"""
    data: Optional[T] = Field(default=None, description="Response data")

class ErrorResponse(ResponseBase):
    """Error response model"""
    success: bool = Field(default=False, description="Request failed")
    error_code: Optional[str] = Field(default=None, description="Error code")
    details: Optional[Any] = Field(default=None, description="Error details")

class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Page size")

class PaginationMeta(BaseModel):
    """Pagination metadata"""
    total: int = Field(description="Total records")
    page: int = Field(description="Current page")
    page_size: int = Field(description="Page size")
    total_pages: int = Field(description="Total pages")
    has_next: bool = Field(description="Has next page")
    has_prev: bool = Field(description="Has previous page")

class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response model"""
    success: bool = Field(default=True, description="Request success")
    message: str = Field(default="Success", description="Response message")
    data: List[T] = Field(default_factory=list, description="Data list")
    meta: PaginationMeta = Field(description="Pagination info")

class BaseSchema(BaseModel):
    """Base Schema with common fields"""
    id: UUID = Field(description="Record ID")
    created_at: datetime = Field(description="Created time")
    updated_at: datetime = Field(description="Updated time")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }

class TokenResponse(BaseModel):
    """JWT Token response"""
    access_token: str = Field(description="Access token")
    refresh_token: str = Field(description="Refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Expiration time in seconds")
