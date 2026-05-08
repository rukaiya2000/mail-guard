"""LLM prompts for email classification with versioning."""

# Prompt versions with improvements
CLASSIFICATION_PROMPTS = {
    "v1": """Analyze the following email and classify it as one of three categories:
- PHISHING: Attempts to steal credentials, personal info, or financial data
- SPAM: Unsolicited marketing, promotional, or commercial content
- LEGITIMATE: Genuine business or personal correspondence

Email to analyze:
{email}

Respond in JSON format:
{{
    "label": "PHISHING" | "SPAM" | "LEGITIMATE",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation"
}}""",

    "v2": """Analyze the following email and classify it into one of three categories based on threat indicators:

Categories:
- PHISHING: Attempts to steal credentials, personal/financial info, or deceive recipients
  - Look for: Urgency, spoofed headers, fake links, requests for passwords
- SPAM: Unsolicited marketing, promotional, or commercial content
  - Look for: Mass marketing language, unsubscribe links, promotional offers
- LEGITIMATE: Genuine business or personal correspondence
  - Look for: Proper formatting, real sender, relevant content, no suspicious links

Email to analyze:
{email}

Provide detailed analysis. Respond ONLY in JSON format:
{{
    "label": "PHISHING" | "SPAM" | "LEGITIMATE",
    "confidence": 0.0-1.0,
    "reasoning": "Detailed explanation of classification decision",
    "threat_indicators": ["indicator1", "indicator2"],
    "recommendation": "Action to take"
}}""",

    "v3": """You are an expert email security analyst. Analyze the email below and classify it.

Categories:
1. PHISHING (Malicious): Credential theft, account compromise, financial fraud, data exfiltration
2. SPAM (Unsolicited): Marketing, promotions, mass emails without legitimate business purpose
3. LEGITIMATE (Safe): Genuine business communication, authorized notifications, trusted contacts

Email to analyze:
<email>
{email}
</email>

Analysis framework:
1. Sender verification: Check From header, SPF/DKIM authenticity
2. Content analysis: Sense of urgency, suspicious links, attachment types
3. Context: Is this expected from this sender?
4. Red flags: Misspellings, domain spoofing, unusual requests

Respond in ONLY this JSON format (no additional text):
{{
    "label": "PHISHING" | "SPAM" | "LEGITIMATE",
    "confidence": 0.0-1.0,
    "reasoning": "Clear, concise explanation"
}}""",
}

# Model configurations with costs
MODEL_CONFIG = {
    "gpt-4": {
        "name": "GPT-4",
        "provider": "openai",
        "cost_per_1k_tokens": 0.03,
        "prompt_cost_per_1k_tokens": 0.03,
        "completion_cost_per_1k_tokens": 0.06,
        "max_tokens": 8096,
        "timeout": 60,
    },
    "gpt-4-turbo": {
        "name": "GPT-4 Turbo",
        "provider": "openai",
        "cost_per_1k_tokens": 0.01,
        "prompt_cost_per_1k_tokens": 0.01,
        "completion_cost_per_1k_tokens": 0.03,
        "max_tokens": 128000,
        "timeout": 60,
    },
    "gpt-3.5-turbo": {
        "name": "GPT-3.5 Turbo",
        "provider": "openai",
        "cost_per_1k_tokens": 0.002,
        "prompt_cost_per_1k_tokens": 0.0005,
        "completion_cost_per_1k_tokens": 0.0015,
        "max_tokens": 16384,
        "timeout": 30,
    },
    "llama-3.1-70b-instruct": {
        "name": "Llama 3.1 70B",
        "provider": "litellm",
        "cost_per_1k_tokens": 0.0007,
        "prompt_cost_per_1k_tokens": 0.0007,
        "completion_cost_per_1k_tokens": 0.0007,
        "max_tokens": 8192,
        "timeout": 30,
    },
    "claude-3-opus": {
        "name": "Claude 3 Opus",
        "provider": "anthropic",
        "cost_per_1k_tokens": 0.015,
        "prompt_cost_per_1k_tokens": 0.015,
        "completion_cost_per_1k_tokens": 0.075,
        "max_tokens": 200000,
        "timeout": 60,
    },
}


def get_prompt(prompt_version: str = "v2") -> str:
    """Get classification prompt by version."""
    if prompt_version not in CLASSIFICATION_PROMPTS:
        raise ValueError(f"Unknown prompt version: {prompt_version}. Available: {list(CLASSIFICATION_PROMPTS.keys())}")
    return CLASSIFICATION_PROMPTS[prompt_version]


def get_model_config(model: str) -> dict:
    """Get model configuration."""
    if model not in MODEL_CONFIG:
        raise ValueError(f"Unknown model: {model}. Available: {list(MODEL_CONFIG.keys())}")
    return MODEL_CONFIG[model]


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate API cost for a classification."""
    config = get_model_config(model)
    prompt_cost = (prompt_tokens / 1000) * config["prompt_cost_per_1k_tokens"]
    completion_cost = (completion_tokens / 1000) * config["completion_cost_per_1k_tokens"]
    return round(prompt_cost + completion_cost, 6)


def get_available_models() -> list[str]:
    """Get list of available models."""
    return list(MODEL_CONFIG.keys())


def get_available_prompts() -> list[str]:
    """Get list of available prompt versions."""
    return list(CLASSIFICATION_PROMPTS.keys())
