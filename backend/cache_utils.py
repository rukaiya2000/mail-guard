import hashlib
from datetime import datetime, timedelta
from database import SessionLocal, ClassificationLog


def hash_email(email_text: str) -> str:
    """Create hash of email for duplicate detection."""
    return hashlib.sha256(email_text.encode()).hexdigest()


def get_cached_classification(email_hash: str, user_id: int = None, cache_hours: int = 24):
    """Check if email was already classified within cache period."""
    db = SessionLocal()
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=cache_hours)

        query = db.query(ClassificationLog).filter(
            ClassificationLog.email_hash == email_hash,
            ClassificationLog.timestamp >= cutoff_time,
            ClassificationLog.success == True,
        )

        if user_id:
            query = query.filter(ClassificationLog.user_id == user_id)

        result = query.order_by(ClassificationLog.timestamp.desc()).first()
        return result
    finally:
        db.close()


def cache_classification(
    email_text: str,
    email_hash: str,
    label: str,
    confidence: float,
    reasoning: str,
    latency_ms: float,
    tokens_used: int,
    user_id: int = None,
):
    """Store classification result with email hash for future lookups."""
    db = SessionLocal()
    try:
        log = ClassificationLog(
            user_id=user_id,
            email_hash=email_hash,
            timestamp=datetime.utcnow(),
            email_snippet=email_text[:200],
            label=label,
            confidence=confidence,
            reasoning=reasoning,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            success=True,
        )
        db.add(log)
        db.commit()
    finally:
        db.close()
