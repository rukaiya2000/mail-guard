"""Route modules for SecureAI Sentinel API."""

from fastapi import APIRouter
from .auth import router as auth_router
from .classify import router as classify_router
from .analytics import router as analytics_router
from .health import router as health_router
from .gmail import router as gmail_router
from .oauth import router as oauth_router
from .feedback import router as feedback_router
from .patterns import router as patterns_router
from .threats import router as threats_router
from .abtest import router as abtest_router
from .ensemble import router as ensemble_router
from .model_comparison import router as model_comparison_router
from .active_learning import router as active_learning_router
from .adversarial import router as adversarial_router

all_routers = [
    auth_router,
    classify_router,
    analytics_router,
    health_router,
    gmail_router,
    oauth_router,
    feedback_router,
    patterns_router,
    threats_router,
    abtest_router,
    ensemble_router,
    model_comparison_router,
    active_learning_router,
    adversarial_router,
]


def register_routes(app):
    """Register all routes to the FastAPI app."""
    for router in all_routers:
        app.include_router(router)
