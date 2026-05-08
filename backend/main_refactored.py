"""FastAPI application entry point for SecureAI Sentinel."""

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import settings
from logger_config import logger
from database import init_db
from routes import register_routes

app = FastAPI(
    title="SecureAI Sentinel",
    version="1.0.0",
    description="AI-powered email threat detection and LLM monitoring platform"
)

# Setup rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Session middleware for OAuth
session_secret = settings.JWT_SECRET or "dev-secret-key-change-in-production"
if not settings.JWT_SECRET:
    logger.warning("JWT_SECRET not set. Using development default (INSECURE FOR PRODUCTION)")

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    from fastapi import HTTPException
    return HTTPException(
        status_code=429,
        detail="Too many requests. Please try again later."
    )


@app.on_event("startup")
def startup_event():
    """Initialize database on startup."""
    logger.info("Starting SecureAI Sentinel API")
    init_db()
    logger.info("Database initialized")


@app.on_event("shutdown")
def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down SecureAI Sentinel API")


# Register all routes
register_routes(app)


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {settings.API_HOST}:{settings.API_PORT}")
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
