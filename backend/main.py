from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse
from pydantic import BaseModel
from datetime import datetime
from collections import defaultdict
import os
import base64
import httpx
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv

from classifier import classify_email, get_classifications
from auth import create_access_token, get_current_user, get_optional_user, CurrentUser
from export_utils import export_to_csv, export_to_pdf
from email_parser import parse_email_headers, extract_email_addresses
from activity_logger import log_activity

load_dotenv()

app = FastAPI(title="SecureAI Sentinel", version="1.0.0")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("JWT_SECRET", "your-secret-key-change-in-production"),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile https://www.googleapis.com/auth/gmail.readonly"},
)


class EmailRequest(BaseModel):
    email_text: str


class BatchEmailRequest(BaseModel):
    emails: list[str]


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


@app.get("/auth/google")
async def google_auth(request: Request):
    redirect_uri = "http://localhost:8000/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/google/callback")
async def google_callback(request: Request):
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
    google_access_token = token.get("access_token")

    jwt_token = create_access_token(google_id, name, email, google_access_token)

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(
        url=f"{frontend_url}?token={jwt_token}&username={name}",
        status_code=302,
    )


@app.get("/me")
def get_me(current_user: CurrentUser = Depends(get_current_user)):
    return {
        "google_id": current_user.google_id,
        "username": current_user.username,
        "email": current_user.email,
    }


@app.get("/gmail/inbox")
async def get_gmail_inbox(current_user: CurrentUser = Depends(get_current_user)):
    if not current_user.google_access_token:
        raise HTTPException(status_code=400, detail="Google access token not found. Please log in again.")

    try:
        headers = {"Authorization": f"Bearer {current_user.google_access_token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers=headers,
                params={"maxResults": 20, "labelIds": "INBOX"},
            )
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Gmail API error: {response.text}")

            message_ids = response.json().get("messages", [])
            emails = []

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
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch Gmail inbox: {str(e)}")


@app.post("/parse-email", response_model=EmailParseResponse)
def parse_email(request: EmailParseRequest):
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
def classify(
    request: EmailRequest,
    current_user: CurrentUser = Depends(get_optional_user),
):
    if not request.email_text.strip():
        raise HTTPException(status_code=400, detail="email_text cannot be empty")

    user_id = current_user.google_id if current_user else None
    result = classify_email(request.email_text, user_id=user_id)
    log_activity("classify", user_id=user_id, details=f"Label: {result.get('label')}")
    return result


@app.post("/classify-batch")
def classify_batch(
    request: BatchEmailRequest,
    current_user: CurrentUser = Depends(get_optional_user),
):
    if not request.emails:
        raise HTTPException(status_code=400, detail="emails list cannot be empty")
    if len(request.emails) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 emails per batch")

    user_id = current_user.google_id if current_user else None
    results = []
    for email in request.emails:
        try:
            result = classify_email(email, user_id=user_id)
            results.append({"success": True, "data": result})
        except Exception as e:
            results.append({"success": False, "error": str(e)})

    return {"total": len(request.emails), "results": results}


@app.get("/metrics", response_model=MetricsResponse)
def get_metrics(current_user: CurrentUser = Depends(get_optional_user)):
    all_logs = get_classifications()
    logs = [c for c in all_logs if c["success"]]
    if current_user:
        logs = [c for c in logs if c["user_id"] == current_user.google_id]

    if not logs:
        return MetricsResponse(total_calls=0, average_latency_ms=0.0, error_rate=0.0, total_tokens_used=0, estimated_cost=0.0)

    total_calls = len(logs)
    average_latency_ms = sum(c["latency_ms"] for c in logs) / total_calls
    total_tokens_used = sum(c["tokens_used"] for c in logs)

    total_attempted = len(all_logs)
    error_count = sum(1 for c in all_logs if not c["success"])
    error_rate = (error_count / total_attempted * 100) if total_attempted > 0 else 0.0
    estimated_cost = (total_tokens_used / 1000) * 0.002

    return MetricsResponse(
        total_calls=total_calls,
        average_latency_ms=round(average_latency_ms, 2),
        error_rate=round(error_rate, 2),
        total_tokens_used=total_tokens_used,
        estimated_cost=round(estimated_cost, 4),
    )


@app.get("/history", response_model=list[HistoryItem])
def get_history(
    label: str = None,
    search: str = None,
    start_date: str = None,
    end_date: str = None,
    confidence_min: float = None,
    current_user: CurrentUser = Depends(get_optional_user),
):
    logs = [c for c in get_classifications() if c["success"]]

    if current_user:
        logs = [c for c in logs if c["user_id"] == current_user.google_id]
    if label and label.upper() != 'ALL':
        logs = [c for c in logs if c["label"] == label.upper()]
    if search:
        logs = [c for c in logs if search.lower() in c["email_snippet"].lower()]
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            logs = [c for c in logs if c["timestamp"] >= start]
        except Exception:
            pass
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            logs = [c for c in logs if c["timestamp"] <= end]
        except Exception:
            pass
    if confidence_min is not None:
        confidence_min = max(0.0, min(1.0, confidence_min))
        logs = [c for c in logs if c["confidence"] >= confidence_min]

    logs = sorted(logs, key=lambda c: c["timestamp"], reverse=True)[:50]

    return [
        HistoryItem(
            timestamp=c["timestamp"],
            label=c["label"],
            confidence=c["confidence"],
            email_snippet=c["email_snippet"],
        )
        for c in logs
    ]


@app.get("/analytics")
def get_analytics(
    start_date: str = None,
    end_date: str = None,
    current_user: CurrentUser = Depends(get_optional_user),
):
    logs = [c for c in get_classifications() if c["success"]]
    if current_user:
        logs = [c for c in logs if c["user_id"] == current_user.google_id]

    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            logs = [c for c in logs if c["timestamp"] >= start]
        except Exception:
            pass
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            logs = [c for c in logs if c["timestamp"] <= end]
        except Exception:
            pass

    if not logs:
        return {"distribution": {"PHISHING": 0, "SPAM": 0, "LEGITIMATE": 0}, "trends": [], "top_hours": []}

    distribution = defaultdict(int)
    for c in logs:
        distribution[c["label"]] += 1

    hourly_data = defaultdict(lambda: {"count": 0, "avg_confidence": []})
    for c in logs:
        hour = c["timestamp"].strftime("%Y-%m-%d %H:00")
        hourly_data[hour]["count"] += 1
        hourly_data[hour]["avg_confidence"].append(c["confidence"])

    trends = []
    for hour in sorted(hourly_data.keys())[-24:]:
        data = hourly_data[hour]
        trends.append({
            "time": hour,
            "count": data["count"],
            "avg_confidence": sum(data["avg_confidence"]) / len(data["avg_confidence"]),
        })

    top_hours = sorted(hourly_data.items(), key=lambda x: x[1]["count"], reverse=True)[:5]
    top_hours = [{"time": k, "count": v["count"]} for k, v in top_hours]

    return {"distribution": dict(distribution), "trends": trends, "top_hours": top_hours}


@app.get("/export/csv")
def export_csv(
    label: str = None,
    current_user: CurrentUser = Depends(get_optional_user),
):
    logs = [c for c in get_classifications() if c["success"]]
    if current_user:
        logs = [c for c in logs if c["user_id"] == current_user.google_id]
    if label and label.upper() != 'ALL':
        logs = [c for c in logs if c["label"] == label.upper()]

    logs = sorted(logs, key=lambda c: c["timestamp"], reverse=True)[:500]

    if not logs:
        raise HTTPException(status_code=404, detail="No classifications to export")

    csv_data = export_to_csv(logs)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=classifications.csv"},
    )


@app.get("/export/pdf")
def export_pdf(
    label: str = None,
    current_user: CurrentUser = Depends(get_optional_user),
):
    logs = [c for c in get_classifications() if c["success"]]
    if current_user:
        logs = [c for c in logs if c["user_id"] == current_user.google_id]
    if label and label.upper() != 'ALL':
        logs = [c for c in logs if c["label"] == label.upper()]

    logs = sorted(logs, key=lambda c: c["timestamp"], reverse=True)[:500]

    if not logs:
        raise HTTPException(status_code=404, detail="No classifications to export")

    user_name = current_user.username if current_user else "User"
    pdf_data = export_to_pdf(logs, user_name=user_name)
    return StreamingResponse(
        iter([pdf_data]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=report.pdf"},
    )


@app.get("/")
def root():
    return {"message": "SecureAI Sentinel API", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
