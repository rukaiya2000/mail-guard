# SecureAI Sentinel

An AI-powered email threat detection tool that classifies emails as phishing, spam, or legitimate using LLMs. Authenticate with Google to classify emails directly from your Gmail inbox.

## Features

- **Email Classifier** — Classifies emails as PHISHING, SPAM, or LEGITIMATE with confidence scores and reasoning
- **Gmail Integration** — Sign in with Google to fetch and classify emails from your inbox

## Quick Start

### Backend

```bash
cd backend
cp .env.example .env        # Add your API keys
uv sync
uv run python main.py       # Runs on http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                 # Runs on http://localhost:3000
```

## Authentication

Login is via **Google OAuth only** — no username/password. The Google access token is embedded in the JWT so Gmail access works without a database.

## Environment Variables

```
OPENAI_API_KEY=        # API key for LiteLLM proxy
LITELLM_BASE_URL=      # LiteLLM base URL (default: https://api.ai.it.ufl.edu)
JWT_SECRET=            # Secret key for signing JWTs
GOOGLE_CLIENT_ID=      # Google OAuth client ID
GOOGLE_CLIENT_SECRET=  # Google OAuth client secret
FRONTEND_URL=          # Frontend URL for OAuth redirect (default: http://localhost:3000)
```

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/auth/google` | — | Start Google OAuth flow |
| GET | `/me` | Required | Current user info |
| GET | `/gmail/inbox` | Required | Fetch Gmail inbox |
| POST | `/classify` | Optional | Classify a single email |

## How Classification Works

1. Email text is hashed — if classified within the last 24h, returns cached result
2. The prompt from `prompts.txt` is sent to the LLM with the email content
3. The LLM returns a JSON with `label`, `confidence`, and `reasoning`
4. Result is stored in-memory (resets on server restart)

To change the classification prompt, just edit `backend/prompts.txt`.

## Confidence Score

The confidence (0.0–1.0) is decided by the LLM based on how many threat signals it finds. There is no separate scoring logic — the model self-reports its certainty.

## Notes

- No database is used — users are identified via Google ID embedded in the JWT
- All endpoints live in `main.py`
