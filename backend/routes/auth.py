"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from database import get_db, User
from schemas import RegisterRequest, LoginRequest, AuthResponse, UserResponse
from auth import hash_password, verify_password, create_access_token, get_current_user
from validators import validate_password_strength, validate_username
from activity_logger import log_activity
from logger_config import logger

router = APIRouter(prefix="/api/v1", tags=["authentication"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=AuthResponse)
@limiter.limit("5/minute")
def register(request: Request, register_request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user. Rate limited to 5 per minute."""
    is_valid, error_msg = validate_username(register_request.username)
    if not is_valid:
        log_activity("register", details=f"Failed: {error_msg}", status="failed")
        raise HTTPException(status_code=400, detail=error_msg)

    is_valid, error_msg = validate_password_strength(register_request.password)
    if not is_valid:
        log_activity("register", details=f"Failed: weak password", status="failed")
        raise HTTPException(status_code=400, detail=error_msg)

    if db.query(User).filter(User.username == register_request.username).first():
        log_activity("register", details="Failed: username already exists", status="failed")
        raise HTTPException(status_code=400, detail="Username already exists")

    if db.query(User).filter(User.email == register_request.email).first():
        log_activity("register", details="Failed: email already exists", status="failed")
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(
        username=register_request.username,
        email=register_request.email,
        hashed_password=hash_password(register_request.password),
        role="user"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_activity("register", user_id=user.id, details=f"New user: {register_request.username}", status="success")
    logger.info(f"New user registered: {register_request.username}")

    token = create_access_token(user.id, user.username)
    return AuthResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
    )


@router.post("/login", response_model=AuthResponse)
@limiter.limit("10/minute")
def login(request: Request, login_request: LoginRequest, db: Session = Depends(get_db)):
    """Login with username and password. Rate limited to 10 per minute."""
    user = db.query(User).filter(User.username == login_request.username).first()
    if not user or not verify_password(login_request.password, user.hashed_password):
        log_activity("login", details=f"Failed login attempt for {login_request.username}", status="failed")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user.id, user.username)
    log_activity("login", user_id=user.id, details=f"Logged in: {login_request.username}", status="success")
    logger.info(f"User logged in: {login_request.username}")

    return AuthResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at,
    )
