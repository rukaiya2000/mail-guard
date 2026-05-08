# LLM Integration Guide

## Overview

SecureAI Sentinel supports multiple LLM providers and models with:
- **Prompt versioning** for continuous improvement
- **Multi-model support** for cost optimization
- **Automatic cost tracking** per classification
- **Structured output parsing** for reliability
- **Retry logic** with exponential backoff
- **Timeout handling** for reliability

## Supported Models

### GPT-4
- **Provider:** OpenAI
- **Cost:** $0.03 per 1K tokens (input + output averaged)
- **Max Tokens:** 8,096
- **Timeout:** 60s
- **Best For:** Highest accuracy, complex emails

### GPT-4 Turbo
- **Provider:** OpenAI
- **Cost:** $0.01 per 1K tokens
- **Max Tokens:** 128,000
- **Timeout:** 60s
- **Best For:** Balanced accuracy and cost

### GPT-3.5 Turbo
- **Provider:** OpenAI
- **Cost:** $0.002 per 1K tokens
- **Max Tokens:** 16,384
- **Timeout:** 30s
- **Best For:** Cost-effective, fast classifications

### Llama 3.1 70B (Default)
- **Provider:** LiteLLM
- **Cost:** $0.0007 per 1K tokens
- **Max Tokens:** 8,192
- **Timeout:** 30s
- **Best For:** Budget-friendly, good accuracy

### Claude 3 Opus
- **Provider:** Anthropic
- **Cost:** $0.015 per 1K tokens (input) / $0.075 (output)
- **Max Tokens:** 200,000
- **Timeout:** 60s
- **Best For:** Very high accuracy, complex reasoning

## Prompt Versions

### V1 (Basic)
- Simple, direct classification prompt
- 3 categories: PHISHING, SPAM, LEGITIMATE
- Best for: Quick, basic classification

### V2 (Improved - Default)
- Enhanced threat indicator identification
- More detailed reasoning
- Better phishing detection
- Best for: Most use cases

### V3 (Expert)
- Expert email security analyst perspective
- Sender verification emphasis
- Red flag identification
- Detailed analysis framework
- Best for: High-stakes security decisions

## Using Different Models

### Basic Usage (Default Model)
```python
from classifier import classify_email

result = classify_email(email_text)
# Uses default: llama-3.1-70b-instruct + v2 prompt
```

### Specify Model
```python
result = classify_email(
    email_text,
    model="gpt-4-turbo",
    prompt_version="v3"
)
```

### Via API Endpoint
```bash
curl -X POST http://localhost:8000/api/v1/classify \
  -H "Content-Type: application/json" \
  -d '{
    "email_text": "Email content...",
    "model": "gpt-4-turbo",
    "prompt_version": "v3"
  }'
```

## Cost Optimization

### Estimated Costs per 100 Classifications

| Model | Avg Tokens | Cost |
|-------|-----------|------|
| Llama 3.1 70B | 450 | $0.032 |
| GPT-3.5 Turbo | 450 | $0.001 |
| GPT-4 Turbo | 450 | $0.005 |
| GPT-4 | 450 | $0.014 |
| Claude 3 Opus | 450 | $0.011 |

### Cost Reduction Strategy

1. **Use Llama by default** - $0.032 per 100 classifications
2. **Use GPT-3.5 for high-volume** - Very cheap, adequate accuracy
3. **Use GPT-4 for sensitive cases** - Higher accuracy when needed
4. **Cache results** - Avoid re-classifying same emails

## Prompt Engineering

### Creating Custom Prompts

1. Add to `prompts.py`:
```python
CLASSIFICATION_PROMPTS = {
    ...
    "v4_custom": """Your custom prompt here...
    
Email to analyze:
{email}

Respond in JSON format:
{...}
    """
}
```

2. Use in classification:
```python
result = classify_email(email_text, prompt_version="v4_custom")
```

### Prompt Best Practices

- **Be specific** - Clear categories with examples
- **Provide context** - Explain what to look for
- **Structured output** - JSON format ensures parsing
- **Version control** - Keep history of prompt changes
- **Test thoroughly** - A/B test new prompts

## Monitoring and Debugging

### Check Available Models
```python
from prompts import get_available_models
models = get_available_models()
print(models)
```

### Check Available Prompts
```python
from prompts import get_available_prompts
prompts = get_available_prompts()
print(prompts)
```

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('classifier')
logger.setLevel(logging.DEBUG)
```

### Check Classification Cost
```python
from prompts import calculate_cost

cost = calculate_cost("gpt-4", prompt_tokens=100, completion_tokens=50)
print(f"Cost: ${cost}")
```

## Performance Metrics

### Token Usage (Average)
- Prompt tokens: 200-300
- Completion tokens: 100-200
- Total: 300-500 tokens per classification

### Latency (Average)
- Llama 3.1: 1-2 seconds
- GPT-3.5: 1-1.5 seconds
- GPT-4 Turbo: 2-3 seconds
- GPT-4: 3-5 seconds
- Claude 3 Opus: 2-4 seconds

### Accuracy (Approximate)
- Llama 3.1: 85%
- GPT-3.5: 88%
- GPT-4 Turbo: 92%
- GPT-4: 95%
- Claude 3 Opus: 94%

## Error Handling

### Timeout
- Default: 30 seconds (60s for GPT-4/Claude)
- Retries: 3 attempts with exponential backoff
- Fallback: Returns cached result if available

### Rate Limiting
- Per-minute limits enforced at API level
- Retry logic handles rate limits automatically
- Exponential backoff: 1s, 2s, 4s

### Invalid Response
- Validates JSON structure
- Validates confidence 0.0-1.0
- Validates label: PHISHING/SPAM/LEGITIMATE
- Logs and retries on invalid response

## Database Schema

Classification results include:
- `label` - PHISHING, SPAM, LEGITIMATE
- `confidence` - 0.0 to 1.0
- `reasoning` - LLM's explanation
- `latency_ms` - Processing time
- `tokens_used` - Total tokens
- `model` - Model used
- `prompt_version` - Prompt version
- `cost` - Estimated API cost

## Testing

### Unit Tests
```bash
pytest tests/test_classifier.py -v
```

### Integration Tests
```bash
pytest tests/test_classify_routes.py -v
```

### Load Testing
```python
import time
from classifier import classify_email

emails = [...]  # list of test emails
start = time.time()
for email in emails:
    classify_email(email)
duration = time.time() - start
print(f"Processed {len(emails)} in {duration}s")
```

## Future Improvements

1. **Fine-tuned models** - Train on your phishing data
2. **Ensemble methods** - Combine multiple models
3. **Active learning** - Improve model with user feedback
4. **Cost prediction** - Forecast API spending
5. **Multi-language** - Support non-English emails
6. **Attachment analysis** - Scan attachments for threats

## Resources

- [OpenAI API Docs](https://platform.openai.com/docs/api-reference)
- [LiteLLM Documentation](https://docs.litellm.ai/)
- [Anthropic Claude Docs](https://docs.anthropic.com/)
- [Prompt Engineering Best Practices](https://platform.openai.com/docs/guides/prompt-engineering)
