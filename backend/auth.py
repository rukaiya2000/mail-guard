import jwt
from datetime import datetime, timedelta
from dataclasses import dataclass
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    google_id: str
    username: str
    email: str
    google_access_token: str | None = None


def create_access_token(google_id: str, username: str, email: str, google_access_token: str | None = None) -> str:
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "google_id": google_id,
        "username": username,
        "email": email,
        "google_access_token": google_access_token,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials) -> dict:
    try:
        return jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> CurrentUser:
    payload = verify_token(credentials)
    return CurrentUser(
        google_id=payload["google_id"],
        username=payload["username"],
        email=payload["email"],
        google_access_token=payload.get("google_access_token"),
    )


def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(optional_security)) -> CurrentUser | None:
    if not credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return CurrentUser(
            google_id=payload["google_id"],
            username=payload["username"],
            email=payload["email"],
            google_access_token=payload.get("google_access_token"),
        )
    except Exception:
        return None
