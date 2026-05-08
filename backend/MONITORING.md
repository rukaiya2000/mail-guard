# Monitoring & Logging Guide

## Logging Configuration

### Log Levels

- **DEBUG** - Detailed diagnostic information
- **INFO** - General informational messages
- **WARNING** - Warning messages for potential issues
- **ERROR** - Error messages for failures
- **CRITICAL** - Critical failures requiring immediate attention

### Log Files

Logs are stored in `/logs/sentinel_YYYYMMDD.log`

Features:
- Automatic daily rotation
- Max 10MB per file (5 backups kept)
- ISO 8601 timestamp format
- Both console and file output

### View Logs

```bash
# View today's logs
tail -f logs/sentinel_$(date +%Y%m%d).log

# Search for errors
grep ERROR logs/sentinel_*.log

# Search for user activity
grep "user_id: 123" logs/sentinel_*.log

# Follow live logs
tail -f logs/sentinel_$(date +%Y%m%d).log | grep ERROR
```

## Security Event Logging

### Security Events Captured

1. **Authentication**
   - New user registration
   - Successful login
   - Failed login attempts
   - Token expiration
   - Google OAuth linking

2. **Authorization**
   - Admin access attempts
   - Unauthorized access
   - Role changes

3. **Data Access**
   - Bulk exports (CSV/PDF)
   - Admin activity access
   - Classification access

4. **Errors**
   - API errors
   - Database errors
   - Timeout errors
   - Classification failures

### Security Log Format

```
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "event_type": "security",
  "action": "login",
  "user_id": 123,
  "username": "john_doe",
  "status": "success|failed",
  "details": {...},
  "ip_address": "192.168.1.100"
}
```

## Monitoring Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "service": "SecureAI Sentinel"
}
```

### Metrics Dashboard
```bash
curl http://localhost:8000/api/v1/metrics
```

Returns:
- Total API calls
- Average latency
- Error rate
- Total tokens used
- Estimated cost

## Performance Monitoring

### Key Metrics to Track

#### Latency
```python
{
  "endpoint": "/api/v1/classify",
  "p50": 1000,  # 50th percentile (median)
  "p95": 2500,  # 95th percentile
  "p99": 4000,  # 99th percentile
  "avg": 1234
}
```

Target: < 2 seconds for single classification

#### Throughput
```python
{
  "endpoint": "/api/v1/classify",
  "requests_per_minute": 50,
  "requests_per_hour": 3000,
  "daily": 72000
}
```

#### Error Rate
```python
{
  "endpoint": "/api/v1/classify",
  "error_rate": 0.5,  # percentage
  "timeout_rate": 0.1,
  "invalid_response_rate": 0.2
}
```

Target: < 2% error rate

### Prometheus Metrics (Optional)

To enable Prometheus integration, add to `main.py`:

```python
from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)

# Custom metrics
classification_counter = Counter(
    'classifications_total',
    'Total classifications',
    ['label', 'model']
)

classification_latency = Histogram(
    'classification_latency_seconds',
    'Classification latency'
)
```

## Rate Limit Monitoring

### Current Limits

- Classification: 10/minute per IP
- Batch: 5/minute per IP
- Register: 5/minute per IP
- Login: 10/minute per IP

### Monitoring Rate Limits

```python
# Check rate limit headers
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1705324245
```

## Database Monitoring

### Query Performance

Enable slow query logging:

```python
# In config.py
SLOW_QUERY_THRESHOLD_MS = 1000

# In logger_config.py
if duration_ms > SLOW_QUERY_THRESHOLD_MS:
    logger.warning(f"Slow query ({duration_ms}ms): {query}")
```

### Connection Pool

Monitor PostgreSQL connections:

```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

## Alert Configuration

### Critical Alerts

1. **Error Rate > 5%**
   - Indicates system issues
   - Action: Investigate logs

2. **Latency p99 > 5s**
   - Performance degradation
   - Action: Check database/LLM

3. **Token Usage Spike**
   - Unusual API usage
   - Action: Check for abuse

4. **Failed Logins > 10/hour**
   - Potential brute force
   - Action: Rate limit/alert

### Warning Alerts

1. **Error Rate > 2%**
2. **Average Latency > 2s**
3. **Database connections > 80%**
4. **Disk space < 20%**

## Integration Examples

### Slack Alerts
```python
import requests

def send_slack_alert(message):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    requests.post(webhook_url, json={"text": message})

# Usage
if error_rate > 0.05:
    send_slack_alert(f"Alert: Error rate is {error_rate*100}%")
```

### Email Alerts
```python
from email.mime.text import MIMEText
import smtplib

def send_email_alert(subject, message):
    msg = MIMEText(message)
    msg["Subject"] = subject
    
    with smtplib.SMTP(os.getenv("SMTP_SERVER")) as server:
        server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
        server.send_message(msg, to_addrs=[os.getenv("ALERT_EMAIL")])
```

### Datadog Integration
```python
from datadog import initialize, api

options = {
    'api_key': os.getenv("DATADOG_API_KEY"),
    'app_key': os.getenv("DATADOG_APP_KEY")
}
initialize(**options)

api.Metric.send(
    metric="sentinel.classification.latency",
    points=[(timestamp, latency_ms)],
    tags=["service:sentinel"]
)
```

## Log Analysis

### Common Log Queries

```bash
# Find all errors from yesterday
grep "ERROR" logs/sentinel_$(date -d yesterday +%Y%m%d).log

# Count errors by type
grep "ERROR" logs/sentinel_*.log | \
  awk -F':' '{print $NF}' | \
  sort | uniq -c

# Find slow classifications
grep "latency" logs/sentinel_*.log | \
  awk '$NF > 3000 {print}'

# Count failed logins
grep "login.*failed" logs/sentinel_*.log | wc -l

# Find database errors
grep "database\|sqlalchemy" logs/sentinel_*.log
```

### Log Shipping

To ship logs to centralized service:

```python
# config.py
LOG_SHIPPING_ENABLED = os.getenv("LOG_SHIPPING_ENABLED", "false").lower() == "true"
LOG_SHIPPING_URL = os.getenv("LOG_SHIPPING_URL")

# logger_config.py
if settings.LOG_SHIPPING_ENABLED:
    http_handler = logging.handlers.HTTPHandler(
        host=settings.LOG_SHIPPING_URL,
        url="/logs",
        method="POST"
    )
    logger.addHandler(http_handler)
```

## Dashboard Setup

### Grafana Dashboard

Example dashboard JSON:
```json
{
  "title": "SecureAI Sentinel",
  "panels": [
    {
      "title": "Requests/min",
      "targets": [{"expr": "rate(http_requests_total[1m])"}]
    },
    {
      "title": "Latency p95",
      "targets": [{"expr": "http_request_duration_seconds{quantile=\"0.95\"}"}]
    },
    {
      "title": "Error Rate",
      "targets": [{"expr": "rate(http_requests_total{status=~\"5..\"}[1m])"}]
    },
    {
      "title": "Classifications/hour",
      "targets": [{"expr": "rate(classifications_total[1h])"}]
    }
  ]
}
```

## Troubleshooting

### High Latency
1. Check LLM API status
2. Check database connections
3. Check network latency
4. Review slow query logs

### High Error Rate
1. Check error logs for patterns
2. Verify API credentials
3. Check rate limiting
4. Review recent code changes

### Memory Leaks
1. Monitor memory usage over time
2. Check for unclosed connections
3. Review logging memory usage
4. Profile with memory_profiler

## Best Practices

1. **Log at appropriate levels** - Don't log everything at ERROR
2. **Include context** - User ID, request ID, timestamp
3. **Sanitize sensitive data** - Never log passwords or tokens
4. **Use structured logging** - JSON format for parsing
5. **Set retention policy** - Delete old logs (30+ days)
6. **Monitor logs actively** - Review alerts daily
7. **Test alerting** - Ensure alerts work when triggered
8. **Document incidents** - Keep incident response log
