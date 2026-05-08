"""Health check and status routes."""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "SecureAI Sentinel"
    }


@router.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "SecureAI Sentinel API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }
