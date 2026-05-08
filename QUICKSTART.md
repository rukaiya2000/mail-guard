# 🚀 SecureAI Sentinel - Quick Start Guide

## One-Command Setup (if you're in a hurry)

**macOS/Linux:**
```bash
# Terminal 1 - Backend
cd secure-ai-sentinel/backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && cp .env.example .env && python main.py

# Terminal 2 - Frontend
cd secure-ai-sentinel/frontend && npm install && npm run dev
```

**Windows:**
```bash
# Terminal 1 - Backend
cd secure-ai-sentinel\backend && python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt && copy .env.example .env && python main.py

# Terminal 2 - Frontend
cd secure-ai-sentinel\frontend && npm install && npm run dev
```

---

## 5-Minute Setup (Recommended)

### Step 1: Edit Backend Config (1 min)
```bash
cd backend
cp .env.example .env
nano .env  # or open with your editor
```

**Add your API key:**
```
OPENAI_API_KEY=sk-xxx...
LITELLM_BASE_URL=https://api.ai.it.ufl.edu
JWT_SECRET=your-secret-key
```

### Step 2: Start Backend (2 min)
```bash
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

✅ **Backend running at:** http://localhost:8000

### Step 3: Start Frontend (2 min)
```bash
cd frontend
npm install
npm run dev
```

✅ **Frontend running at:** http://localhost:3000

### Step 4: Open App
Open your browser and go to: **http://localhost:3000**

---

## Default Ports

| Service | URL | Status |
|---------|-----|--------|
| **Frontend** | http://localhost:3000 | Browser |
| **Backend** | http://localhost:8000 | API |
| **API Docs** | http://localhost:8000/docs | Swagger UI |

---

## First Steps in App

1. **Register Account** - Click "Sign up"
   - Username: testuser
   - Email: test@example.com
   - Password: testpass123

2. **Test Classification** - Go to "Email Classifier"
   - Paste this sample email:
   ```
   Subject: Urgent: Verify Your Account
   From: security@paypal-verify.com
   
   Dear User,
   Please verify your account by clicking below:
   https://verify-account.paypal-update.com/user=123456
   ```
   - Click "Classify Email"

3. **Try Batch Mode** - Go to "Batch Classifier"
   - Paste 2-3 emails (one per line)
   - Click "Classify Batch"

4. **View Analytics** - Go to "Analytics"
   - See charts of your classifications

5. **Export Results** - Go back to "Email Classifier"
   - Click "📊 CSV" or "📄 PDF" to download

---

## Troubleshooting Quick Fixes

### Backend won't start
```bash
# Install missing dependencies
pip install -r requirements.txt

# Check if port 8000 is free
# Windows: netstat -ano | findstr :8000
# macOS/Linux: lsof -i :8000
```

### Frontend won't start
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### API key error
```bash
# Verify .env file exists
ls backend/.env

# Check content
cat backend/.env
# Should have OPENAI_API_KEY=...
```

### Can't access frontend
- Make sure backend is running first
- Try http://localhost:3000 in private/incognito mode
- Clear browser cache

---

## What Each Tab Does

| Tab | Purpose | What You Can Do |
|-----|---------|----------------|
| **Dashboard** | Live metrics | See call count, latency, error rate, costs |
| **Email Classifier** | Single email | Paste email → get threat classification |
| **Batch Classifier** | Multiple emails | Classify 2-50 emails at once |
| **Analytics** | Data analysis | View threat distribution & trends |
| **About** | Project info | Learn about the system |

---

## Advanced: Keep Windows Open

After setup, to keep things running:

**Terminal 1 (Backend)**
```bash
cd secure-ai-sentinel/backend
source venv/bin/activate
python main.py
```
Keep this terminal open with backend running.

**Terminal 2 (Frontend)**
```bash
cd secure-ai-sentinel/frontend
npm run dev
```
Keep this terminal open with frontend running.

**Terminal 3 (Optional - for git/other work)**
```bash
cd secure-ai-sentinel
# Do other work here
```

Now you can make changes and see them reload automatically!

---

## Environment Variables

### Required
```
OPENAI_API_KEY       # Your API key (starts with sk-)
LITELLM_BASE_URL     # Usually: https://api.ai.it.ufl.edu
JWT_SECRET           # Any random string for security
```

### Optional
```
API_HOST             # Default: 0.0.0.0
API_PORT             # Default: 8000
```

---

## Development Workflow

```bash
# Terminal 1: Start backend with auto-reload
cd backend
source venv/bin/activate
python main.py

# Terminal 2: Start frontend with hot reload
cd frontend
npm run dev

# Terminal 3: Edit code
# - Python files auto-reload in backend
# - React files auto-reload in frontend
```

---

## Quick Commands

```bash
# Stop backend
Ctrl + C

# Stop frontend
Ctrl + C

# Deactivate Python venv
deactivate

# Reset database (delete all data)
rm backend/sentinel.db

# Update dependencies
pip install -r requirements.txt --upgrade
npm update

# View API documentation
# Open: http://localhost:8000/docs
```

---

## Useful Links

- **Full Setup Guide:** [SETUP.md](./SETUP.md)
- **API Docs:** http://localhost:8000/docs
- **API Docs (ReDoc):** http://localhost:8000/redoc
- **Full README:** [README.md](./README.md)
- **FastAPI:** https://fastapi.tiangolo.com/
- **React:** https://react.dev/

---

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| `npm: command not found` | Install [Node.js](https://nodejs.org/) |
| `Port 3000 in use` | Kill process: `lsof -i :3000 \| grep LISTEN \| awk '{print $2}' \| xargs kill -9` |
| `API key error` | Check `.env` file, verify key format |
| `Can't connect to backend` | Make sure `python main.py` is running |
| `Hot reload not working` | Refresh browser (Ctrl+R) |
| `Database error` | Delete `backend/sentinel.db` and restart |

---

## Next Steps

1. ✅ Get it running (you're here!)
2. 📖 Read [SETUP.md](./SETUP.md) for detailed info
3. 🧪 Test the app with sample emails
4. 📊 Export your first report
5. 🔧 Customize for your needs
6. 🚀 Deploy to production (when ready)

---

## Need Help?

1. Check [SETUP.md](./SETUP.md) - Detailed troubleshooting section
2. Check [README.md](./README.md) - Feature documentation
3. Look at the "About" tab in the app
4. Review terminal error messages
5. Check browser console (F12)

---

**Enjoy SecureAI Sentinel! 🛡️**
