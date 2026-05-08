"""Email classification routes."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from database import get_db, User
from schemas import EmailRequest, BatchEmailRequest, ClassificationResult, EmailParseRequest, EmailParseResponse
from classifier import classify_email
from auth import get_optional_user
from email_parser import parse_email_headers, extract_email_addresses
from activity_logger import log_activity
from logger_config import logger

router = APIRouter(prefix="/api/v1", tags=["classification"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/parse-email", response_model=EmailParseResponse)
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


@router.post("/classify", response_model=ClassificationResult)
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
        result = classify_email(
            email_request.email_text,
            user_id=user_id,
            gmail_message_id=email_request.gmail_message_id
        )
        log_activity("classify", user_id=user_id, details=f"Label: {result.get('label')}", status="success")
        logger.info(f"Classification successful for user {user_id}: {result.get('label')}")
        return result
    except Exception as e:
        logger.error(f"Classification failed for user {user_id}: {str(e)}")
        log_activity("classify", user_id=user_id, details=f"Error: {str(e)}", status="failed")
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@router.post("/classify-batch")
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
    logger.info(f"Batch classification completed for user {user_id}: {len(batch_request.emails)} emails")
    return {"total": len(batch_request.emails), "results": results}
