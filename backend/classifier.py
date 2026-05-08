import openai
import json
import time
from datetime import datetime
from database import SessionLocal, ClassificationLog
from cache_utils import hash_email, get_cached_classification
import os


def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY", "your_api_key")
    base_url = os.getenv("LITELLM_BASE_URL", "https://api.ai.it.ufl.edu")

    return openai.OpenAI(
        api_key=api_key,
        base_url=base_url
    )


def classify_email(email_text: str, user_id: int = None, gmail_message_id: str = None):
    """Classify email as phishing, spam, or legitimate using LLM."""
    # Check cache for duplicate emails
    email_hash = hash_email(email_text)
    cached_result = get_cached_classification(email_hash, user_id=user_id, cache_hours=24)

    if cached_result:
        return {
            "label": cached_result.label,
            "confidence": cached_result.confidence,
            "reasoning": cached_result.reasoning,
            "latency_ms": cached_result.latency_ms,
            "tokens_used": cached_result.tokens_used,
            "cached": True,
        }

    client = get_openai_client()

    prompt = f"""Analyze the following email and classify it as one of three categories:
    - PHISHING: Attempts to steal credentials, personal info, or financial data
    - SPAM: Unsolicited marketing, promotional, or commercial content
    - LEGITIMATE: Genuine business or personal correspondence

Email to analyze:
{email_text}

Respond in JSON format:
{{
    "label": "PHISHING" | "SPAM" | "LEGITIMATE",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation"
}}"""

    start_time = time.time()

    try:
        response = client.chat.completions.create(
            model="llama-3.1-70b-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        latency_ms = (time.time() - start_time) * 1000
        tokens_used = response.usage.total_tokens

        # Parse response
        content = response.choices[0].message.content
        result = json.loads(content)

        # Normalize label to uppercase
        label = result.get("label", "").upper()
        confidence = float(result.get("confidence", 0.0))
        reasoning = result.get("reasoning", "")

        # Log to database
        db = SessionLocal()
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
            gmail_message_id=gmail_message_id
        )
        db.add(log)
        db.commit()
        db.close()

        return {
            "label": label,
            "confidence": confidence,
            "reasoning": reasoning,
            "latency_ms": latency_ms,
            "tokens_used": tokens_used
        }

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000

        # Log failure
        db = SessionLocal()
        log = ClassificationLog(
            user_id=user_id,
            email_hash=email_hash,
            timestamp=datetime.utcnow(),
            email_snippet=email_text[:200],
            label="ERROR",
            confidence=0.0,
            reasoning="",
            latency_ms=latency_ms,
            tokens_used=0,
            success=False,
            error_message=str(e),
            gmail_message_id=gmail_message_id
        )
        db.add(log)
        db.commit()
        db.close()

        raise Exception(f"Classification failed: {str(e)}")
