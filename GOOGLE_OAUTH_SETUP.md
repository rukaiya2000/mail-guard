# Google OAuth Setup Guide

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click the project dropdown at the top
3. Click **"NEW PROJECT"**
4. Enter a project name (e.g., "SecureAI Sentinel")
5. Click **"CREATE"**
6. Wait for the project to be created

## Step 2: Set Up OAuth Consent Screen

1. In the left sidebar, go to **APIs & Services → OAuth consent screen**
2. Select **"External"** (for development)
3. Click **"CREATE"**
4. Fill in the form:
   - **App name**: SecureAI Sentinel
   - **User support email**: your-email@example.com
   - **Developer contact**: your-email@example.com
5. Click **"SAVE AND CONTINUE"** (skip optional scopes)
6. Click **"SAVE AND CONTINUE"** again
7. Click **"BACK TO DASHBOARD"**

## Step 3: Create OAuth Credentials

1. In the left sidebar, go to **APIs & Services → Credentials**
2. Click **"CREATE CREDENTIALS"** → **"OAuth Client ID"**
3. Select **"Web application"**
4. Under **"Authorized redirect URIs"**, click **"ADD URI"**
5. Enter: `http://localhost:8000/auth/google/callback`
6. Click **"CREATE"**
7. **Copy the Client ID and Client Secret** — you'll need them in the next step

## Step 4: Add Credentials to Your App

1. Open `backend/.env` in your editor
2. Replace the placeholder values with your actual credentials:
   ```
   GOOGLE_CLIENT_ID=your-client-id-here
   GOOGLE_CLIENT_SECRET=your-client-secret-here
   FRONTEND_URL=http://localhost:3000
   ```
3. Save the file

## Step 5: Restart the Backend

```bash
cd backend
source venv/bin/activate
# Kill the running server (Ctrl+C) and restart
python main.py
```

## Step 6: Test It

1. Go to `http://localhost:3000`
2. Click **"Continue with Google"**
3. You'll be redirected to Google
4. Sign in with your Google account
5. You should be redirected back and logged in!

## Troubleshooting

- **"redirect_uri_mismatch" error**: Make sure the redirect URI in Google Cloud Console matches exactly: `http://localhost:8000/auth/google/callback`
- **"Client ID not found" error**: Make sure you added the correct values to `.env` and restarted the backend
- **CORS error**: The backend allows all origins, so this shouldn't happen. Check your browser console for details
