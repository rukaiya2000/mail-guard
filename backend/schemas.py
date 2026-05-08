"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class EmailRequest(BaseModel):
    """Request schema for single email classification."""
    email_text: str = Field(..., min_length=10, max_length=100000)
    gmail_message_id: Optional[str] = Field(None, max_length=500)

    @property
    def email_text_clean(self) -> str:
        return self.email_text.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "email_text": "Full email content here...",
                "gmail_message_id": "abc123xyz"
            }
        }


class BatchEmailRequest(BaseModel):
    """Request schema for batch email classification."""
    emails: list[str] = Field(..., min_items=1, max_items=50)

    class Config:
        json_schema_extra = {
            "example": {
                "emails": ["Email 1 content...", "Email 2 content..."]
            }
        }


class RegisterRequest(BaseModel):
    """Request schema for user registration."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john@example.com",
                "password": "SecurePass123!"
            }
        }


class LoginRequest(BaseModel):
    """Request schema for user login."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)

    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "SecurePass123!"
            }
        }


class AuthResponse(BaseModel):
    """Response schema for authentication endpoints."""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


class UserResponse(BaseModel):
    """Response schema for user info."""
    id: int
    username: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class EmailParseRequest(BaseModel):
    """Request schema for email parsing."""
    email_text: str

    class Config:
        json_schema_extra = {
            "example": {
                "email_text": "Full email content..."
            }
        }


class EmailParseResponse(BaseModel):
    """Response schema for email parsing."""
    headers: dict
    body: str
    is_html: bool
    extracted_addresses: list[str]


class ClassificationResult(BaseModel):
    """Response schema for email classification."""
    label: str
    confidence: float
    reasoning: str
    latency_ms: float
    tokens_used: int
    cached: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "label": "PHISHING",
                "confidence": 0.95,
                "reasoning": "Email attempts to steal credentials",
                "latency_ms": 1234.5,
                "tokens_used": 450,
                "cached": False
            }
        }


class MetricsResponse(BaseModel):
    """Response schema for metrics endpoint."""
    total_calls: int
    average_latency_ms: float
    error_rate: float
    total_tokens_used: int
    estimated_cost: float

    class Config:
        json_schema_extra = {
            "example": {
                "total_calls": 42,
                "average_latency_ms": 1287.34,
                "error_rate": 2.38,
                "total_tokens_used": 18900,
                "estimated_cost": 0.0378
            }
        }


class HistoryItem(BaseModel):
    """Schema for classification history items."""
    timestamp: datetime
    label: str
    confidence: float
    email_snippet: str

    class Config:
        from_attributes = True


class ActivityLogResponse(BaseModel):
    """Schema for activity log items."""
    id: int
    action: str
    details: Optional[str]
    timestamp: datetime
    status: str

    class Config:
        from_attributes = True
