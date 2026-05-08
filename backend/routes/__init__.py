"""Route modules for SecureAI Sentinel API."""

from fastapi import APIRouter
from .auth import router as auth_router
from .classify import router as classify_router
from .analytics import router as analytics_router
from .health import router as health_router
from .gmail import router as gmail_router
from .oauth import router as oauth_router

all_routers = [
    auth_router,
    classify_router,
    analytics_router,
    health_router,
    gmail_router,
    oauth_router,
]


def register_routes(app):
    """Register all routes to the FastAPI app."""
    for router in all_routers:
        app.include_router(router)
