import openai
import json
import time
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_PROMPT = open(os.path.join(os.path.dirname(__file__), "prompts.txt")).read()
MODEL = "llama-3.1-70b-instruct"


def classify_email(email_text: str, user_id: Optional[str] = None) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    base_url = os.getenv("LITELLM_BASE_URL", "https://api.ai.it.ufl.edu")
    client = openai.OpenAI(api_key=api_key, base_url=base_url)

    prompt = _PROMPT.format(email=email_text)
    start_time = time.time()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        timeout=30,
    )

    latency_ms = (time.time() - start_time) * 1000
    content = response.choices[0].message.content

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON from LLM: {content[:200]}")

    label = result.get("label", "").upper()
    if label not in ["PHISHING", "SPAM", "LEGITIMATE"]:
        raise ValueError(f"Unexpected label: {label}")

    return {
        "label": label,
        "confidence": float(result.get("confidence", 0.0)),
        "reasoning": result.get("reasoning", ""),
        "latency_ms": latency_ms,
        "tokens_used": response.usage.total_tokens,
    }
