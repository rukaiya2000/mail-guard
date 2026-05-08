"""OAuth authentication routes."""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
import os
from database import get_db, User
from auth import create_access_token
from activity_logger import log_activity
from logger_config import logger

router = APIRouter(tags=["oauth"])

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile https://www.googleapis.com/auth/gmail.readonly"},
)


@router.get("/auth/google")
async def google_auth(request: Request):
    """Redirect to Google OAuth consent screen."""
    redirect_uri = f"http://localhost:8000/auth/google/callback"
    try:
        return await oauth.google.authorize_redirect(request, redirect_uri)
    except Exception as e:
        logger.error(f"Google auth redirect failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to redirect to Google OAuth")


@router.get("/auth/google/callback")
async def google_callback(request: Request, db: Session = Session()):
    """Handle Google OAuth callback."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        logger.error(f"Failed to exchange code for token: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to exchange code for token: {str(e)}")

    user_info = token.get("userinfo")
    if not user_info:
        logger.error("Failed to get user info from Google")
        raise HTTPException(status_code=400, detail="Failed to get user info from Google")

    google_id = user_info.get("sub")
    email = user_info.get("email")
    name = user_info.get("name", email.split("@")[0] if email else "User")

    user = db.query(User).filter(User.google_id == google_id).first()

    if not user:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                username=name,
                email=email,
                google_id=google_id,
                google_access_token=token.get("access_token"),
                hashed_password=None,
                role="user"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            log_activity("register", user_id=user.id, details=f"New Google user: {name}", status="success")
            logger.info(f"New Google user registered: {name}")
        else:
            user.google_id = google_id
            user.google_access_token = token.get("access_token")
            db.commit()
            log_activity("login", user_id=user.id, details="Linked Google account", status="success")
            logger.info(f"Linked Google account for user {name}")
    else:
        user.google_access_token = token.get("access_token")
        db.commit()
        log_activity("login", user_id=user.id, details="Google login", status="success")
        logger.info(f"Google user logged in: {name}")

    jwt_token = create_access_token(user.id, user.username)
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

    return RedirectResponse(
        url=f"{frontend_url}?token={jwt_token}&user_id={user.id}&username={user.username}",
        status_code=302
    )
