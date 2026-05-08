import openai
import json
import time
import logging
from datetime import datetime
from database import SessionLocal, ClassificationLog
from cache_utils import hash_email, get_cached_classification
from prompts import get_prompt, get_model_config, calculate_cost
import os
from typing import Optional

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 1
TIMEOUT_SECONDS = 30


def get_openai_client(base_url: Optional[str] = None):
    """Get OpenAI client with configured API key and base URL."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    if not base_url:
        base_url = os.getenv("LITELLM_BASE_URL", "https://api.ai.it.ufl.edu")

    return openai.OpenAI(api_key=api_key, base_url=base_url)


def _validate_classification_result(result: dict) -> bool:
    """Validate that the classification result has required fields."""
    required_fields = ["label", "confidence", "reasoning"]
    if not all(field in result for field in required_fields):
        return False

    label = result.get("label", "").upper()
    if label not in ["PHISHING", "SPAM", "LEGITIMATE"]:
        return False

    try:
        confidence = float(result.get("confidence", -1))
        if not (0.0 <= confidence <= 1.0):
            return False
    except (ValueError, TypeError):
        return False

    return True


def _parse_llm_response(content: str) -> dict:
    """Parse and validate LLM response JSON."""
    try:
        result = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {content[:200]}")
        raise ValueError(f"Invalid JSON response from LLM: {str(e)}")

    if not _validate_classification_result(result):
        logger.error(f"Invalid classification result structure: {result}")
        raise ValueError("Classification result missing required fields or invalid values")

    return result


def _log_classification(email_text: str, email_hash: str, user_id: Optional[int],
                       label: str, confidence: float, reasoning: str,
                       latency_ms: float, tokens_used: int, success: bool,
                       error_message: Optional[str] = None,
                       gmail_message_id: Optional[str] = None,
                       model: str = "llama-3.1-70b-instruct",
                       prompt_version: str = "v2"):
    """Log classification result to database."""
    try:
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
            success=success,
            error_message=error_message,
            gmail_message_id=gmail_message_id,
            model=model,
            prompt_version=prompt_version
        )
        db.add(log)
        db.commit()
        db.close()
    except Exception as e:
        logger.error(f"Failed to log classification to database: {str(e)}")


def classify_email(email_text: str, user_id: Optional[int] = None,
                  gmail_message_id: Optional[str] = None,
                  model: str = "llama-3.1-70b-instruct",
                  prompt_version: str = "v2") -> dict:
    """
    Classify email as phishing, spam, or legitimate using LLM.

    Args:
        email_text: Email content to classify
        user_id: User ID for data isolation
        gmail_message_id: Gmail message ID if from Gmail
        model: LLM model to use (default: llama-3.1-70b-instruct)
        prompt_version: Prompt version to use (default: v2)

    Implements:
    - Caching to avoid duplicate classifications
    - Retry logic with exponential backoff
    - Timeout handling
    - Comprehensive error handling and logging
    - Multiple model support with cost tracking
    """
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
            "model": model,
            "prompt_version": prompt_version,
        }

    # Get prompt template and format it
    prompt_template = get_prompt(prompt_version)
    prompt = prompt_template.format(email=email_text)

    # Get model configuration
    try:
        model_config = get_model_config(model)
    except ValueError as e:
        logger.error(f"Invalid model: {str(e)}")
        raise ValueError(f"Invalid model: {model}")

    start_time = time.time()
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            client = get_openai_client()
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                timeout=model_config["timeout"]
            )

            latency_ms = (time.time() - start_time) * 1000
            tokens_used = response.usage.total_tokens
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens

            content = response.choices[0].message.content
            result = _parse_llm_response(content)

            label = result.get("label", "").upper()
            confidence = float(result.get("confidence", 0.0))
            reasoning = result.get("reasoning", "")

            # Calculate cost
            estimated_cost = calculate_cost(model, prompt_tokens, completion_tokens)

            _log_classification(
                email_text, email_hash, user_id,
                label, confidence, reasoning,
                latency_ms, tokens_used, True, None, gmail_message_id,
                model=model, prompt_version=prompt_version
            )

            return {
                "label": label,
                "confidence": confidence,
                "reasoning": reasoning,
                "latency_ms": latency_ms,
                "tokens_used": tokens_used,
                "model": model,
                "prompt_version": prompt_version,
                "cost": estimated_cost,
            }

        except (openai.Timeout, openai.APIConnectionError) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"Timeout/connection error (attempt {attempt + 1}/{MAX_RETRIES}), retrying in {wait_time}s: {str(e)}")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed after {MAX_RETRIES} retries: {str(e)}")

        except ValueError as e:
            last_error = e
            logger.error(f"Invalid response format: {str(e)}")
            break

        except openai.RateLimitError as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"Rate limited (attempt {attempt + 1}/{MAX_RETRIES}), retrying in {wait_time}s")
                time.sleep(wait_time)
            else:
                logger.error(f"Rate limit exceeded after {MAX_RETRIES} retries")

        except (openai.APIError, openai.AuthenticationError) as e:
            last_error = e
            logger.error(f"API error: {str(e)}")
            break

        except Exception as e:
            last_error = e
            logger.error(f"Unexpected error during classification: {str(e)}")
            break

    latency_ms = (time.time() - start_time) * 1000
    error_msg = str(last_error) if last_error else "Unknown error"

    _log_classification(
        email_text, email_hash, user_id,
        "ERROR", 0.0, "",
        latency_ms, 0, False, error_msg, gmail_message_id,
        model=model, prompt_version=prompt_version
    )

    raise Exception(f"Classification failed after {MAX_RETRIES} attempts: {error_msg}")
