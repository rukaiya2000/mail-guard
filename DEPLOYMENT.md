# Deployment Guide

## Pre-Deployment Checklist

- [ ] All tests passing: `pytest`
- [ ] Frontend builds: `npm run build`
- [ ] Environment variables configured
- [ ] Database backups created
- [ ] SSL/TLS certificates ready
- [ ] Security scan completed
- [ ] Performance tested

## Environment Variables

### Backend (.env)
```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_URL=postgresql://user:password@localhost/sentinel

# JWT Security
JWT_SECRET=<generate-strong-random-key>

# CORS Configuration
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# LLM Configuration
OPENAI_API_KEY=<your-api-key>
LITELLM_BASE_URL=https://api.ai.it.ufl.edu
LLM_MODEL=gpt-4-turbo

# Google OAuth
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>
FRONTEND_URL=https://yourdomain.com

# Logging
LOG_LEVEL=INFO
```

### Frontend (.env)
```env
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_ENABLE_GMAIL_INBOX=true
VITE_LOG_LEVEL=warn
```

## Docker Deployment

### Backend Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile
```dockerfile
FROM node:18-alpine as build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q -O- http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
```

### Docker Compose
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: sentinel
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: sentinel
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sentinel"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://sentinel:${DB_PASSWORD}@db:5432/sentinel
      JWT_SECRET: ${JWT_SECRET}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ALLOWED_ORIGINS: ${ALLOWED_ORIGINS}
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./backend/logs:/app/logs
    restart: unless-stopped

  frontend:
    build: ./frontend
    environment:
      VITE_API_BASE_URL: http://localhost:8000
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
```

## AWS Deployment

### RDS PostgreSQL
```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier sentinel-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --allocated-storage 20 \
  --master-username admin \
  --master-user-password "${DB_PASSWORD}" \
  --db-name sentinel
```

### ECS Deployment
```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name sentinel

# Create task definition (use task-definition.json)
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create service
aws ecs create-service \
  --cluster sentinel \
  --service-name sentinel-backend \
  --task-definition sentinel-backend:1 \
  --desired-count 2 \
  --launch-type FARGATE
```

### CloudFront/S3 (Frontend)
```bash
# Create S3 bucket
aws s3 mb s3://sentinel-frontend

# Upload build artifacts
aws s3 sync ./frontend/dist s3://sentinel-frontend/

# Create CloudFront distribution
aws cloudfront create-distribution --distribution-config file://cloudfront-config.json
```

## Database Migration

### PostgreSQL Setup
```bash
# Connect to database
psql -h sentinel-db.c123456.us-east-1.rds.amazonaws.com -U admin -d sentinel

# Create tables (auto-created on first run by SQLAlchemy)
python -c "from database import init_db; init_db()"
```

### Backup and Restore
```bash
# Backup
pg_dump -h localhost -U sentinel -d sentinel > sentinel_backup.sql

# Restore
psql -h localhost -U sentinel -d sentinel < sentinel_backup.sql
```

## SSL/TLS Configuration

### Self-Signed Certificates (Development)
```bash
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
```

### Let's Encrypt (Production)
```bash
# Using certbot with nginx
sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

### Nginx Configuration
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

## Monitoring Setup

### Prometheus
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'sentinel'
    static_configs:
      - targets: ['localhost:8000']
```

### Grafana Dashboard
Import dashboard JSON from `monitoring/grafana-dashboard.json`

## Scaling

### Horizontal Scaling
```bash
# Scale backend instances
aws ecs update-service \
  --cluster sentinel \
  --service sentinel-backend \
  --desired-count 5
```

### Load Balancing
```bash
# Create load balancer
aws elbv2 create-load-balancer \
  --name sentinel-lb \
  --subnets subnet-12345678 subnet-87654321
```

### Database Connection Pooling
```python
# config.py
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True
)
```

## Rollback Procedure

### Docker Rollback
```bash
# Stop current version
docker stop sentinel-backend

# Run previous version
docker run -d --name sentinel-backend \
  --env-file .env \
  sentinel-backend:previous-tag
```

### ECS Rollback
```bash
# Update service with previous task definition
aws ecs update-service \
  --cluster sentinel \
  --service sentinel-backend \
  --task-definition sentinel-backend:previous-version
```

## Performance Tuning

### Database
```sql
-- Create indexes for common queries
CREATE INDEX idx_user_timestamp ON classification_logs(user_id, timestamp);
CREATE INDEX idx_label_timestamp ON classification_logs(label, timestamp);

-- Analyze query plans
EXPLAIN ANALYZE SELECT * FROM classification_logs ...;
```

### Application
```python
# Enable caching
from cachetools import TTLCache

cache = TTLCache(maxsize=1000, ttl=3600)  # 1 hour

# Connection pooling
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_size": 20,
    "pool_recycle": 3600,
    "pool_pre_ping": True
}
```

## Security Hardening

### Remove Debug Mode
```python
# main.py
app = FastAPI(debug=False)
```

### Rate Limiting
```bash
# Already configured in app
# See routes for @limiter.limit() decorators
```

### CORS Configuration
```python
# Only allow specific origins
ALLOWED_ORIGINS = ["https://yourdomain.com"]
```

### Secret Management
```bash
# Use AWS Secrets Manager or similar
aws secretsmanager create-secret \
  --name sentinel/jwt-secret \
  --secret-string '...'
```

## Monitoring and Alerting

### Health Checks
```bash
curl https://yourdomain.com/health
curl https://yourdomain.com/api/v1/health
```

### Log Aggregation
```bash
# Stream logs from ECS
aws logs tail /ecs/sentinel-backend --follow
```

### Error Tracking
- Set up Sentry for error tracking
- Configure email alerts
- Set up Slack notifications

## Post-Deployment

1. **Verify** - Test all endpoints work
2. **Monitor** - Watch logs and metrics for 1 hour
3. **Communicate** - Notify users of deployment
4. **Document** - Update runbook and procedures

## Rollback Decision Tree

```
Is app down?
├─ Yes → Immediate rollback
└─ No → High error rate?
   ├─ Yes (>5%) → Investigate/Rollback
   └─ No → Monitor for 1 hour
```

## Troubleshooting

### Application won't start
- Check logs: `docker logs sentinel-backend`
- Verify environment variables
- Check database connectivity

### High latency
- Check database query performance
- Monitor API response times
- Check LLM provider status

### High memory usage
- Check for memory leaks
- Review connection pools
- Enable garbage collection

## Support and Resources

- Documentation: See README.md, SETUP.md
- Issues: Check logs and MONITORING.md
- Performance: See DATABASE.md for optimization
