"""Gmail integration routes."""

import base64
import httpx
from fastapi import APIRouter, Depends, HTTPException
from authlib.integrations.starlette_client import OAuth

from database import User, get_db
from auth import get_current_user
from logger_config import logger
import os

router = APIRouter(prefix="/api/v1", tags=["gmail"])

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openai email profile https://www.googleapis.com/auth/gmail.readonly"},
)


@router.get("/gmail/inbox")
async def get_gmail_inbox(current_user: User = Depends(get_current_user)):
    """Fetch latest emails from user's Gmail inbox."""
    if not current_user.google_access_token:
        raise HTTPException(status_code=400, detail="Google access token not found. Please log in again.")

    try:
        headers = {"Authorization": f"Bearer {current_user.google_access_token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers=headers,
                params={"maxResults": 20, "labelIds": "INBOX"},
                timeout=30.0,
            )
            if response.status_code != 200:
                logger.error(f"Gmail API error: Status {response.status_code}, Response: {response.text}")
                raise HTTPException(status_code=400, detail=f"Gmail API error: {response.text}")

            message_ids = response.json().get("messages", [])
            emails = []

            for msg in message_ids:
                msg_response = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}",
                    headers=headers,
                    params={"format": "full"},
                    timeout=30.0,
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
                                    try:
                                        body = base64.urlsafe_b64decode(data + "==").decode("utf-8")
                                        break
                                    except Exception as e:
                                        logger.warning(f"Failed to decode email body: {str(e)}")
                    if not body:
                        body_data = msg_data.get("payload", {}).get("body", {}).get("data", "")
                        if body_data:
                            try:
                                body = base64.urlsafe_b64decode(body_data + "==").decode("utf-8")
                            except Exception as e:
                                logger.warning(f"Failed to decode email body: {str(e)}")

                    snippet = msg_data.get("snippet", "")

                    emails.append({
                        "id": msg["id"],
                        "subject": subject,
                        "from": from_addr,
                        "date": date,
                        "snippet": snippet,
                        "body": body or snippet,
                    })

        logger.info(f"Retrieved {len(emails)} emails from Gmail inbox for user {current_user.username}")
        return {"emails": emails}

    except HTTPException:
        raise
    except httpx.TimeoutException:
        logger.error("Gmail API request timed out")
        raise HTTPException(status_code=504, detail="Gmail API request timed out")
    except Exception as e:
        logger.error(f"Gmail inbox error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch Gmail inbox: {str(e)}")
