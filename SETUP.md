# SecureAI Sentinel - Complete Setup Guide

## 📋 Prerequisites

- **Python 3.8+** - [Download](https://www.python.org/downloads/)
- **Node.js 16+** - [Download](https://nodejs.org/)
- **npm** (comes with Node.js)
- **Git** (optional, for version control)

## 🚀 Quick Start (5 minutes)

### 1. Clone/Extract Project
```bash
cd /path/to/secure-ai-sentinel
```

### 2. Start Backend (Terminal 1)
```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env with your settings
nano .env
# (or use your preferred editor)

# Required in .env:
# OPENAI_API_KEY=your_actual_api_key
# LITELLM_BASE_URL=https://api.ai.it.ufl.edu
# JWT_SECRET=your-secret-key-change-in-production

# Start server
python main.py
```

The backend will run on **http://localhost:8000**

### 3. Start Frontend (Terminal 2)
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will run on **http://localhost:3000**

### 4. Open in Browser
- Go to: **http://localhost:3000**
- Register a new account or login
- Start classifying emails!

---

## 🔧 Detailed Setup

### Backend Setup

#### Step 1: Create Virtual Environment
```bash
cd backend
python -m venv venv
```

#### Step 2: Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

#### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 4: Configure Environment
```bash
# Copy example file
cp .env.example .env

# Edit with your API credentials
# Use nano, vim, or your favorite editor
nano .env
```

**Required settings:**
```
OPENAI_API_KEY=sk-xxx (get from LiteLLM)
LITELLM_BASE_URL=https://api.ai.it.ufl.edu
JWT_SECRET=your-random-secret-key-here
```

**Optional settings:**
```
API_HOST=0.0.0.0
API_PORT=8000
```

#### Step 5: Run Backend
```bash
python main.py
```

**Expected output:**
```
Uvicorn running on http://0.0.0.0:8000
Press CTRL+C to quit
```

**Test backend:**
- Open: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

### Frontend Setup

#### Step 1: Install Dependencies
```bash
cd frontend
npm install
```

#### Step 2: Start Development Server
```bash
npm run dev
```

**Expected output:**
```
  VITE v5.0.0  ready in 123 ms

  ➜  Local:   http://localhost:3000/
  ➜  press h to show help
```

#### Step 3: Open in Browser
- Go to: http://localhost:3000
- You should see the SecureAI Sentinel login page

---

## 📝 First Time Setup Checklist

- [ ] Python 3.8+ installed
- [ ] Node.js 16+ installed
- [ ] Backend virtual environment created
- [ ] Backend dependencies installed
- [ ] .env file configured with API key
- [ ] Backend running on http://localhost:8000
- [ ] Frontend dependencies installed
- [ ] Frontend running on http://localhost:3000
- [ ] Can access http://localhost:3000 in browser
- [ ] Can register/login

---

## 🧪 Testing the Application

### 1. Register a New Account
- Click "Sign up" on login page
- Enter username, email, password
- Click "Sign Up"

### 2. Test Email Classification
- Go to "Email Classifier" tab
- Paste a sample email:
```
Subject: Verify Your Account
From: support@yourbank.com
To: user@example.com

Dear User,

Please verify your account by clicking the link below:
https://verify-account-yourbank.com/?user=12345

This is urgent.

Best regards,
Security Team
```
- Click "Classify Email"
- See classification result with confidence score

### 3. Try Batch Classification
- Go to "Batch Classifier" tab
- Paste 2-3 emails (one per line)
- Click "Classify Batch"
- See results summary

### 4. View Analytics
- Go to "Analytics" tab
- See charts and statistics
- Try date range filtering

### 5. Export Results
- Go to "Email Classifier" or "Batch Classifier"
- Click "📊 CSV" to download CSV
- Click "📄 PDF" to download PDF report

---

## 🐛 Troubleshooting

### Backend Won't Start

**Error: "ModuleNotFoundError: No module named 'fastapi'"**
```bash
# Solution: Install dependencies
pip install -r requirements.txt
```

**Error: "Connection refused" when accessing API**
```bash
# Check if backend is running
# Terminal 1 should show: Uvicorn running on http://0.0.0.0:8000
# If not, run: python main.py
```

**Error: "OPENAI_API_KEY not found"**
```bash
# Solution: Check .env file
cat .env
# Should show: OPENAI_API_KEY=your_key_here
```

### Frontend Won't Start

**Error: "npm: command not found"**
```bash
# Solution: Install Node.js from https://nodejs.org/
```

**Error: "Cannot find module '@vitejs/plugin-react'"**
```bash
# Solution: Install dependencies
npm install
```

**Error: "Port 3000 already in use"**
```bash
# Solution 1: Kill process using port 3000
# Windows: netstat -ano | findstr :3000
# macOS/Linux: lsof -i :3000 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Solution 2: Use different port
# Edit frontend/vite.config.js, change port: 3000 to 3001
```

### API Key Issues

**Error: "Invalid API key"**
- Make sure OPENAI_API_KEY is set in .env
- Verify key format: should start with "sk-" or match LiteLLM format
- Test with: curl http://localhost:8000/

**Error: "Connection to LiteLLM failed"**
- Check LITELLM_BASE_URL in .env
- Ensure it's: https://api.ai.it.ufl.edu
- Verify network connectivity

---

## 📊 Database

### SQLite Database
- Location: `backend/sentinel.db`
- Auto-created on first run
- Contains: users, classifications, activity logs

### Reset Database
```bash
# Stop the backend (Ctrl+C)
# Delete the database file
rm backend/sentinel.db
# Restart backend
python main.py
```

---

## 🔐 Security Notes

### Development Only
The current setup is suitable for **development and testing only**.

### For Production
- Change `JWT_SECRET` to a strong random string
- Use PostgreSQL instead of SQLite
- Enable HTTPS
- Restrict CORS origins
- Add rate limiting
- Use environment-specific configs
- Add proper authentication & authorization
- Enable logging & monitoring

---

## 📚 Project Structure

```
secure-ai-sentinel/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── database.py             # SQLAlchemy models
│   ├── classifier.py           # LLM integration
│   ├── auth.py                 # Authentication
│   ├── export_utils.py         # CSV/PDF export
│   ├── email_parser.py         # Email parsing
│   ├── cache_utils.py          # Caching logic
│   ├── activity_logger.py      # Activity tracking
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example            # Environment template
│   └── sentinel.db             # SQLite database (auto-created)
│
├── frontend/
│   ├── src/
│   │   ├── main.jsx            # React entry point
│   │   ├── App.jsx             # Main app component
│   │   ├── ThemeContext.jsx    # Dark mode
│   │   ├── AuthContext.jsx     # Authentication
│   │   ├── index.css           # Tailwind styles
│   │   ├── hooks/
│   │   │   └── useDebounce.js  # Debounce hook
│   │   └── components/
│   │       ├── Dashboard.jsx
│   │       ├── Classifier.jsx
│   │       ├── BatchClassifier.jsx
│   │       ├── Analytics.jsx
│   │       ├── HistoryTable.jsx
│   │       ├── MetricCard.jsx
│   │       ├── Login.jsx
│   │       ├── Register.jsx
│   │       └── About.jsx
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
│
├── README.md                    # Full documentation
├── SETUP.md                     # This file
└── CLAUDE.md                    # Claude Code instructions
```

---

## 🚀 Next Steps

1. **Test the app**: Follow the testing section above
2. **Explore features**: Try all tabs and functionality
3. **Integrate your data**: Use your own emails
4. **Deploy**: When ready, deploy to production (AWS, Heroku, etc.)

---

## 📞 Support

If you encounter issues:
1. Check troubleshooting section above
2. Review error messages in terminal
3. Check browser console (F12) for frontend errors
4. Review backend logs
5. Verify .env configuration

---

## 🎓 Learning Resources

- **FastAPI**: https://fastapi.tiangolo.com/
- **React**: https://react.dev/
- **Tailwind CSS**: https://tailwindcss.com/
- **SQLAlchemy**: https://www.sqlalchemy.org/
- **OpenAI API**: https://platform.openai.com/docs/

---

## 📝 Notes

- Backend and frontend run independently
- Keep both terminals open during development
- Hot reload enabled for both backend and frontend
- Database persists between restarts
- Can access API docs at http://localhost:8000/docs
