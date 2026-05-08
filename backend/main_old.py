from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import StreamingResponse, RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from collections import defaultdict
import httpx
from authlib.integrations.starlette_client import OAuth
import base64
import email
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database import init_db, get_db, ClassificationLog, User, ActivityLog
from classifier import classify_email
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    get_optional_user,
)
from export_utils import export_to_csv, export_to_pdf
from email_parser import parse_email_headers, validate_email_address, extract_email_addresses
from activity_logger import log_activity, get_user_activity, get_all_activity
from logger_config import logger
from auth_utils import require_admin
from validators import validate_password_strength, validate_username

load_dotenv()

app = FastAPI(title="SecureAI Sentinel", version="1.0.0")

# Setup rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return HTTPException(
        status_code=429,
        detail="Too many requests. Please try again later."
    )

# Configure Session Middleware (required for OAuth)
session_secret = os.getenv("JWT_SECRET")
if not session_secret:
    logger.error("JWT_SECRET environment variable is not set. Using development default (INSECURE FOR PRODUCTION)")
    session_secret = "dev-secret-key-change-in-production"

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
)

# Configure CORS with allowed origins
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Configure OAuth
oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile https://www.googleapis.com/auth/gmail.readonly"},
)


class EmailRequest(BaseModel):
    email_text: str = Field(..., min_length=10, max_length=100000)
    gmail_message_id: str | None = Field(None, max_length=500)

    @property
    def email_text_clean(self) -> str:
        return self.email_text.strip()


class BatchEmailRequest(BaseModel):
    emails: list[str] = Field(..., min_items=1, max_items=50)

    class Config:
        json_schema_extra = {
            "example": {
                "emails": ["Email 1 content...", "Email 2 content..."]
            }
        }


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = EmailStr()
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime


class EmailParseRequest(BaseModel):
    email_text: str


class EmailParseResponse(BaseModel):
    headers: dict
    body: str
    is_html: bool
    extracted_addresses: list[str]


class ClassificationResult(BaseModel):
    label: str
    confidence: float
    reasoning: str
    latency_ms: float
    tokens_used: int


class MetricsResponse(BaseModel):
    total_calls: int
    average_latency_ms: float
    error_rate: float
    total_tokens_used: int
    estimated_cost: float


class HistoryItem(BaseModel):
    timestamp: datetime
    label: str
    confidence: float
    email_snippet: str


@app.on_event("startup")
def startup_event():
    init_db()


@app.post("/register", response_model=AuthResponse)
@limiter.limit("5/minute")
def register(request: Request, register_request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user. Rate limited to 5 per minute."""
    # Validate username format
    is_valid, error_msg = validate_username(register_request.username)
    if not is_valid:
        log_activity("register", details=f"Failed: {error_msg}", status="failed")
        raise HTTPException(status_code=400, detail=error_msg)

    # Validate password strength
    is_valid, error_msg = validate_password_strength(register_request.password)
    if not is_valid:
        log_activity("register", details=f"Failed: weak password", status="failed")
        raise HTTPException(status_code=400, detail=error_msg)

    if db.query(User).filter(User.username == register_request.username).first():
        log_activity("register", details=f"Failed: username already exists", status="failed")
        raise HTTPException(status_code=400, detail="Username already exists")

    if db.query(User).filter(User.email == register_request.email).first():
        log_activity("register", details=f"Failed: email already exists", status="failed")
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


@app.post("/login", response_model=AuthResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login with username and password."""
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, user.hashed_password):
        log_activity("login", details=f"Failed login attempt for {request.username}", status="failed")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user.id, user.username)
    log_activity("login", user_id=user.id, details=f"Logged in: {request.username}")

    return AuthResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
    )


@app.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at,
    )


@app.get("/gmail/inbox")
async def get_gmail_inbox(current_user: User = Depends(get_current_user)):
    """Fetch latest emails from user's Gmail inbox."""
    if not current_user.google_access_token:
        raise HTTPException(status_code=400, detail="Google access token not found. Please log in again.")

    try:
        # Get list of messages
        headers = {"Authorization": f"Bearer {current_user.google_access_token}"}
        async with httpx.AsyncClient() as client:
            # Get list of message IDs
            response = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers=headers,
                params={"maxResults": 20, "labelIds": "INBOX"},
            )
            if response.status_code != 200:
                print(f"Gmail API error: Status {response.status_code}, Response: {response.text}")
                raise HTTPException(status_code=400, detail=f"Gmail API error: {response.text}")

            message_ids = response.json().get("messages", [])
            emails = []

            # Fetch full content for each message
            for msg in message_ids:
                msg_response = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}",
                    headers=headers,
                    params={"format": "full"},
                )
                if msg_response.status_code == 200:
                    msg_data = msg_response.json()
                    headers_data = msg_data.get("payload", {}).get("headers", [])
                    subject = next((h["value"] for h in headers_data if h["name"] == "Subject"), "No subject")
                    from_addr = next((h["value"] for h in headers_data if h["name"] == "From"), "Unknown")
                    date = next((h["value"] for h in headers_data if h["name"] == "Date"), "")

                    # Extract body
                    body = ""
                    parts = msg_data.get("payload", {}).get("parts", [])
                    if parts:
                        for part in parts:
                            if part["mimeType"] == "text/plain":
                                data = part.get("body", {}).get("data", "")
                                if data:
                                    body = base64.urlsafe_b64decode(data + "==").decode("utf-8")
                                    break
                    if not body:
                        body = msg_data.get("payload", {}).get("body", {}).get("data", "")
                        if body:
                            body = base64.urlsafe_b64decode(body + "==").decode("utf-8")

                    snippet = msg_data.get("snippet", "")

                    emails.append({
                        "id": msg["id"],
                        "subject": subject,
                        "from": from_addr,
                        "date": date,
                        "snippet": snippet,
                        "body": body or snippet,
                    })

        return {"emails": emails}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Gmail inbox error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch Gmail inbox: {str(e)}")


@app.get("/auth/google")
async def google_auth(request: Request):
    """Redirect to Google OAuth consent screen."""
    redirect_uri = f"http://localhost:8000/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to exchange code for token: {str(e)}")

    user_info = token.get("userinfo")
    if not user_info:
        raise HTTPException(status_code=400, detail="Failed to get user info from Google")

    google_id = user_info.get("sub")
    email = user_info.get("email")
    name = user_info.get("name", email.split("@")[0] if email else "User")

    # Find or create user
    user = db.query(User).filter(User.google_id == google_id).first()

    if not user:
        # Check if email already exists (from previous email/password signup)
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # Create new user
            user = User(
                username=name,
                email=email,
                google_id=google_id,
                google_access_token=token.get("access_token"),
                hashed_password=None,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            log_activity("register", user_id=user.id, details=f"New Google user: {name}")
        else:
            # Link Google account to existing user
            user.google_id = google_id
            user.google_access_token = token.get("access_token")
            db.commit()
            log_activity("login", user_id=user.id, details=f"Linked Google account")
    else:
        # Update access_token on every login (may have been refreshed)
        user.google_access_token = token.get("access_token")
        db.commit()

    # Create JWT token
    jwt_token = create_access_token(user.id, user.username)

    # Redirect to frontend with token in URL
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(
        url=f"{frontend_url}?token={jwt_token}&user_id={user.id}&username={user.username}",
        status_code=302
    )


@app.get("/activity")
def get_activity(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
):
    """Get user's activity logs."""
    logs = get_user_activity(current_user.id, limit=limit)
    return [
        {
            "id": log.id,
            "action": log.action,
            "details": log.details,
            "timestamp": log.timestamp,
            "status": log.status,
        }
        for log in logs
    ]


@app.get("/admin/activity")
def get_admin_activity(
    limit: int = 500,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all activity logs (admin only)."""
    require_admin(current_user)

    logs = get_all_activity(limit=limit)
    logger.info(f"Admin {current_user.username} accessed all activity logs")

    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "details": log.details,
            "timestamp": log.timestamp,
            "status": log.status,
        }
        for log in logs
    ]


@app.post("/parse-email", response_model=EmailParseResponse)
def parse_email(request: EmailParseRequest):
    """Parse email headers and extract key information."""
    if not request.email_text.strip():
        raise HTTPException(status_code=400, detail="email_text cannot be empty")

    parsed = parse_email_headers(request.email_text)
    addresses = extract_email_addresses(request.email_text)

    return EmailParseResponse(
        headers=parsed['headers'],
        body=parsed['body'],
        is_html=parsed['is_html'],
        extracted_addresses=list(set(addresses)),
    )


@app.post("/classify", response_model=ClassificationResult)
@limiter.limit("10/minute")
def classify(
    request: Request,
    email_request: EmailRequest,
    current_user: User = Depends(get_optional_user),
):
    """Classify an email as phishing, spam, or legitimate. Rate limited to 10 per minute."""
    if not email_request.email_text.strip():
        raise HTTPException(status_code=400, detail="email_text cannot be empty")

    user_id = current_user.id if current_user else None
    try:
        result = classify_email(email_request.email_text, user_id=user_id, gmail_message_id=email_request.gmail_message_id)
        log_activity("classify", user_id=user_id, details=f"Label: {result.get('label')}", status="success")
        logger.info(f"Classification successful for user {user_id}: {result.get('label')}")
        return result
    except Exception as e:
        logger.error(f"Classification failed for user {user_id}: {str(e)}")
        log_activity("classify", user_id=user_id, details=f"Error: {str(e)}", status="failed")
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@app.post("/classify-batch")
@limiter.limit("5/minute")
def classify_batch(
    request: Request,
    batch_request: BatchEmailRequest,
    current_user: User = Depends(get_optional_user),
):
    """Classify multiple emails in batch. Rate limited to 5 per minute. Max 50 emails per batch."""
    if not batch_request.emails:
        raise HTTPException(status_code=400, detail="emails list cannot be empty")

    if len(batch_request.emails) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 emails per batch")

    user_id = current_user.id if current_user else None
    results = []
    for email in batch_request.emails:
        try:
            result = classify_email(email, user_id=user_id)
            results.append({"success": True, "data": result})
        except Exception as e:
            results.append({"success": False, "error": str(e)})

    log_activity("classify-batch", user_id=user_id, details=f"Batch of {len(batch_request.emails)} emails", status="success")
    return {"total": len(batch_request.emails), "results": results}


@app.get("/metrics", response_model=MetricsResponse)
def get_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get aggregated metrics from classification history."""
    query = db.query(ClassificationLog).filter(ClassificationLog.success == True)
    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)
    logs = query.all()

    if not logs:
        return MetricsResponse(
            total_calls=0,
            average_latency_ms=0.0,
            error_rate=0.0,
            total_tokens_used=0,
            estimated_cost=0.0
        )

    total_calls = len(logs)
    average_latency_ms = sum(log.latency_ms for log in logs) / total_calls
    total_tokens_used = sum(log.tokens_used for log in logs)

    # Calculate error rate
    total_attempted = db.query(func.count(ClassificationLog.id)).scalar()
    error_count = db.query(func.count(ClassificationLog.id)).filter(
        ClassificationLog.success == False
    ).scalar()
    error_rate = (error_count / total_attempted * 100) if total_attempted > 0 else 0.0

    # Estimate cost ($0.002 per 1k tokens)
    estimated_cost = (total_tokens_used / 1000) * 0.002

    return MetricsResponse(
        total_calls=total_calls,
        average_latency_ms=round(average_latency_ms, 2),
        error_rate=round(error_rate, 2),
        total_tokens_used=total_tokens_used,
        estimated_cost=round(estimated_cost, 4)
    )


@app.get("/history", response_model=list[HistoryItem])
def get_history(
    label: str = None,
    search: str = None,
    start_date: str = None,
    end_date: str = None,
    confidence_min: float = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get classification results with optional filtering."""
    query = db.query(ClassificationLog).filter(ClassificationLog.success == True)

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    if label and label.upper() != 'ALL':
        query = query.filter(ClassificationLog.label == label.upper())

    if search:
        query = query.filter(ClassificationLog.email_snippet.ilike(f"%{search}%"))

    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            query = query.filter(ClassificationLog.timestamp >= start)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid start_date format: {start_date}. Use ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error parsing start_date: {str(e)}")

    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            query = query.filter(ClassificationLog.timestamp <= end)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid end_date format: {end_date}. Use ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error parsing end_date: {str(e)}")

    if confidence_min is not None:
        confidence_min = max(0, min(1, confidence_min))
        query = query.filter(ClassificationLog.confidence >= confidence_min)

    logs = (
        query
        .order_by(ClassificationLog.timestamp.desc())
        .limit(50)
        .all()
    )

    return [
        HistoryItem(
            timestamp=log.timestamp,
            label=log.label,
            confidence=log.confidence,
            email_snippet=log.email_snippet
        )
        for log in logs
    ]


@app.get("/analytics")
def get_analytics(
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get advanced analytics including distribution and trends."""
    query = db.query(ClassificationLog).filter(ClassificationLog.success == True)
    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            query = query.filter(ClassificationLog.timestamp >= start)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid start_date format: {start_date}. Use ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error parsing start_date: {str(e)}")

    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            query = query.filter(ClassificationLog.timestamp <= end)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid end_date format: {end_date}. Use ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error parsing end_date: {str(e)}")

    logs = query.all()

    if not logs:
        return {
            "distribution": {"PHISHING": 0, "SPAM": 0, "LEGITIMATE": 0},
            "trends": [],
            "top_hours": []
        }

    # Distribution
    distribution = defaultdict(int)
    for log in logs:
        distribution[log.label] += 1

    # Trends (hourly)
    hourly_data = defaultdict(lambda: {"count": 0, "avg_confidence": []})
    for log in logs:
        hour = log.timestamp.strftime("%Y-%m-%d %H:00")
        hourly_data[hour]["count"] += 1
        hourly_data[hour]["avg_confidence"].append(log.confidence)

    trends = []
    for hour in sorted(hourly_data.keys())[-24:]:  # Last 24 hours
        data = hourly_data[hour]
        trends.append({
            "time": hour,
            "count": data["count"],
            "avg_confidence": sum(data["avg_confidence"]) / len(data["avg_confidence"])
        })

    # Top hours
    top_hours = sorted(
        hourly_data.items(),
        key=lambda x: x[1]["count"],
        reverse=True
    )[:5]
    top_hours = [{"time": k, "count": v["count"]} for k, v in top_hours]

    return {
        "distribution": dict(distribution),
        "trends": trends,
        "top_hours": top_hours
    }


@app.get("/export/csv")
def export_csv(
    label: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Export classifications as CSV."""
    query = db.query(ClassificationLog).filter(ClassificationLog.success == True)

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    if label and label.upper() != 'ALL':
        query = query.filter(ClassificationLog.label == label.upper())

    logs = query.order_by(ClassificationLog.timestamp.desc()).limit(500).all()

    if not logs:
        raise HTTPException(status_code=404, detail="No classifications to export")

    csv_data = export_to_csv(logs)

    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=classifications.csv"}
    )


@app.get("/export/pdf")
def export_pdf(
    label: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Export classifications as PDF report."""
    query = db.query(ClassificationLog).filter(ClassificationLog.success == True)

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    if label and label.upper() != 'ALL':
        query = query.filter(ClassificationLog.label == label.upper())

    logs = query.order_by(ClassificationLog.timestamp.desc()).limit(500).all()

    if not logs:
        raise HTTPException(status_code=404, detail="No classifications to export")

    user_name = current_user.username if current_user else "User"
    pdf_data = export_to_pdf(logs, user_name=user_name)

    return StreamingResponse(
        iter([pdf_data]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=report.pdf"}
    )


@app.get("/")
def root():
    return {"message": "SecureAI Sentinel API", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
