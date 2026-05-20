from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import os
import base64
import httpx
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv

from classifier import classify_email
from auth import create_access_token, get_current_user, get_optional_user, CurrentUser

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


class ClassificationResult(BaseModel):
    label: str
    confidence: float
    reasoning: str
    latency_ms: float
    tokens_used: int


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


@app.post("/classify", response_model=ClassificationResult)
def classify(
    request: EmailRequest,
    current_user: CurrentUser = Depends(get_optional_user),
):
    if not request.email_text.strip():
        raise HTTPException(status_code=400, detail="email_text cannot be empty")

    user_id = current_user.google_id if current_user else None
    result = classify_email(request.email_text, user_id=user_id)
    return result


@app.get("/")
def root():
    return {"message": "SecureAI Sentinel API", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
