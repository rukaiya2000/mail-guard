# SecureAI Sentinel

A full-stack AI security platform combining LLM provider monitoring with intelligent email threat detection.

## Features

- **Email Threat Classifier**: Uses LLMs to classify emails as phishing, spam, or legitimate with confidence scores and reasoning
- **LLM Monitoring**: Automatically logs all LLM calls with latency, token usage, and costs
- **Real-time Dashboard**: Live metrics dashboard with latency trends and aggregated statistics
- **Classification History**: View the last 50 classifications with timestamps and email snippets with **search & filter**
- **Cost Tracking**: Automatic cost estimation based on token usage ($0.002 per 1k tokens)
- **Batch Classification**: Upload CSV or paste multiple emails for batch processing (up to 50 at a time)
- **Advanced Analytics**: Distribution charts, hourly trends, and peak activity analysis
- **Dark Mode**: Toggle between light and dark themes with persistent storage
- **User Authentication**: Register/login system with JWT tokens and per-user data isolation

## Project Structure

```
secureai-sentinel/
├── backend/
│   ├── main.py              # FastAPI application with endpoints
│   ├── database.py          # SQLAlchemy models and database setup
│   ├── classifier.py        # LLM integration and classification logic
│   ├── requirements.txt     # Python dependencies
│   ├── .env.example         # Environment variables template
│   └── sentinel.db          # SQLite database (generated on first run)
├── frontend/
│   ├── src/
│   │   ├── main.jsx                    # React entry point
│   │   ├── App.jsx                     # Main app component with tabs
│   │   ├── index.css                   # Tailwind CSS import
│   │   └── components/
│   │       ├── Dashboard.jsx           # Metrics dashboard with chart
│   │       ├── Classifier.jsx          # Email classification interface
│   │       ├── HistoryTable.jsx        # Recent classifications table
│   │       └── MetricCard.jsx          # Reusable metric card component
│   ├── index.html           # HTML entry point
│   ├── package.json         # Node.js dependencies
│   ├── vite.config.js       # Vite build configuration
│   ├── tailwind.config.js   # Tailwind CSS configuration
│   └── postcss.config.js    # PostCSS configuration
└── README.md                # This file
```

## ⚡ Quick Start (5 minutes)

### Option A: Docker (Recommended)

```bash
# Set up environment
cp .env.example .env        # Edit with your API key

# Start everything with one command
docker-compose up

# Open browser: http://localhost:3000
```

See **[DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md)** for Docker setup, cloud deployment options, and troubleshooting.

### Option B: Local Development

**See [SETUP.md](./SETUP.md) for detailed instructions**

**Terminal 1 - Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # Edit with your API key
python main.py              # Runs on http://localhost:8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm install
npm run dev                 # Runs on http://localhost:3000
```

**Open browser:** http://localhost:3000

---

## 📋 Full Setup Instructions

For detailed setup, environment configuration, troubleshooting, and more, see **[SETUP.md](./SETUP.md)**.

### What's Covered in SETUP.md:
- ✅ System prerequisites
- ✅ Step-by-step backend setup
- ✅ Step-by-step frontend setup
- ✅ Environment variables configuration
- ✅ Testing the application
- ✅ Common troubleshooting
- ✅ Database management
- ✅ Security notes
- ✅ Project structure
- ✅ Production deployment tips

## 🧠 Advanced AI/ML Features

For comprehensive details on sophisticated machine learning techniques, see:
- **[AI_ML_FEATURES.md](./backend/AI_ML_FEATURES.md)** - Advanced prompt engineering, ensemble classification, confidence calibration
- **[ADVANCED_FEATURES.md](./backend/ADVANCED_FEATURES.md)** - User feedback loops, pattern detection, threat analysis, A/B testing
- **[ACTIVE_LEARNING_AND_ADVERSARIAL.md](./backend/ACTIVE_LEARNING_AND_ADVERSARIAL.md)** - Human-in-the-loop learning, adversarial robustness testing
- **[DRIFT_COST_MONITORING.md](./backend/DRIFT_COST_MONITORING.md)** - Drift detection, cost optimization, real-time monitoring
- **[ML_ARCHITECTURE.md](./backend/ML_ARCHITECTURE.md)** - System design principles, threat analysis pipeline, interview talking points

### Prompt Engineering (v1-v4)
- **v4 (Production)**: Few-shot learning with chain-of-thought reasoning + threat scoring
- **v3 (Expert Mode)**: Analysis framework with structured threat detection
- **v2 (Enhanced)**: Detailed threat indicators and recommendations
- **v1 (Baseline)**: Simple instruction-based classification

### Ensemble Classification
- Combines predictions from GPT-4, Llama, and Claude
- Weighted voting based on model confidence
- Shows consensus percentage and disagreements
- Improves accuracy by 2-5% over single model

```bash
POST /api/v1/classify/ensemble
{
  "email_text": "...",
  "models": ["gpt-4-turbo", "llama-3.1-70b-instruct", "claude-3-opus"]
}
```

### Confidence Calibration
- Measures if model confidence matches actual accuracy
- Bin-based calibration curves to detect over/under-confidence
- Identifies when to trust vs. distrust confidence scores
- Statistical metrics for reliability assessment

```bash
GET /api/v1/models/comparison?days=30
GET /api/v1/models/{model}/calibration
```

### Model Performance Comparison
- Precision, recall, F1 scores by email type
- Confidence-accuracy correlation
- Best model selection per threat category
- Performance trends over time

### Statistical A/B Testing
- Chi-squared tests for prompt version significance
- P-value calculation (p < 0.05 = significant)
- Automatic best prompt selection
- Performance comparison with statistical rigor

### User Feedback Loop
- Mark classifications as correct/incorrect
- Specify correct label if model was wrong
- Tracks accuracy improvements over time
- Enables continuous model learning

### Phishing Pattern Detection
- Most common keywords in phishing emails
- Sender domain analysis and trends
- Daily threat distribution trends
- Risk indicators in high-confidence predictions

### Advanced Threat Analysis
- Multi-dimensional scoring: URLs + Headers + Credentials
- SPF/DKIM/DMARC validation
- Domain spoofing detection
- Credential theft indicators
- Overall threat score (0-1)

### Active Learning (Human-in-the-Loop)
- Automatically flag uncertain predictions (confidence < 0.70)
- Human analysts review and correct flagged emails
- Track accuracy improvement from feedback
- Optimize human effort: review only 12-15% of emails
- Measure impact of human review on model accuracy

```bash
GET /api/v1/active-learning/queue     # Get emails for review
POST /api/v1/active-learning/review/{id}  # Submit corrections
GET /api/v1/active-learning/metrics   # Track improvement
```

### Adversarial Robustness Testing
- Test models against 7 evasion techniques:
  - **Homograph attacks**: amaz0n.com (lookalike characters)
  - **Unicode encoding**: zero-width character injection
  - **Obfuscation**: keyword splitting (ver\nify)
  - **HTML encoding**: &#118;erify (entity encoding)
  - **Typo injection**: Am4z0n (intentional misspellings)
  - **Context confusion**: legitimate language mixed with phishing
  - **Case randomization**: VeRiFy (mixed case)
- Measure robustness score (0-1) for each model
- Benchmark across multiple models
- Ensure models resist real-world attack techniques

```bash
POST /api/v1/adversarial/test-email    # Test single email
POST /api/v1/adversarial/benchmark     # Compare models
GET /api/v1/adversarial/attack-types   # Attack documentation
```

### Model Drift Detection
- Monitor accuracy, confidence, latency, and label distribution over time
- Automatically detect when models degrade
- Alert when retraining is recommended
- Track trends and provide actionable recommendations
- Typical alert: "Accuracy dropped 5% in last 7 days"

```bash
GET /api/v1/drift/status          # Current drift assessment
GET /api/v1/drift/recommendations # Actionable recommendations
```

### Cost Optimization
- Analyze cost-efficiency for each model (accuracy per dollar)
- Identify opportunities to reduce costs 20-30%
- Recommend model selection based on accuracy/cost tradeoff
- Caching analysis to find duplicate classifications
- Monthly cost projection and budgeting

```bash
GET /api/v1/cost/analysis           # Cost breakdown by model
GET /api/v1/cost/optimization-plan  # Savings recommendations
GET /api/v1/cost/caching-analysis   # Caching opportunities
POST /api/v1/cost/model-selector    # Smart model selection
GET /api/v1/cost/monthly-projection # Cost forecasting
```

### Real-Time Monitoring
- Live system health metrics (uptime, latency, errors)
- Hourly performance trends over 24 hours
- Model and label distribution tracking
- SLA compliance checking (99.5% uptime targets)
- Single dashboard endpoint for all metrics

```bash
GET /api/v1/monitoring/realtime        # Quick metrics snapshot
GET /api/v1/monitoring/health          # Health status with alerts
GET /api/v1/monitoring/dashboard       # Complete dashboard data
GET /api/v1/monitoring/sla-compliance  # SLA verification
```

### New Features (v1.0+)

#### 1. Search & Filter
- Filter classification history by threat label (Phishing, Spam, Legitimate)
- Search email snippets by text content
- Real-time filtering without page reload

#### 2. Batch Classification
- Upload CSV files with multiple emails
- Paste multiple emails (one per line)
- Process up to 50 emails per batch
- View detailed results with success/failure status
- See summary statistics including distribution and average confidence

#### 3. Advanced Analytics
- **Distribution Chart**: Pie chart showing phishing, spam, and legitimate percentages
- **Trends Chart**: 24-hour classification trends with volume and confidence metrics
- **Peak Hours**: Identify busiest times for email classification
- **Detailed Stats**: Breakdown of all threat types

### 4. Dark Mode
- Toggle between light and dark themes
- Theme preference persists across sessions
- Respects system dark mode preference on first load

### 5. User Authentication
- User registration with email validation
- Secure login with JWT tokens
- Per-user data isolation (classifications are private to each user)
- Session persistence with local storage
- Logout functionality

## API Endpoints

### Authentication Endpoints

#### POST /register
Create a new user account.

**Request:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user_id": 1,
  "username": "john_doe"
}
```

#### POST /login
Login with credentials and get JWT token.

**Request:**
```json
{
  "username": "john_doe",
  "password": "secure_password"
}
```

**Response:** Same as `/register`

#### GET /me
Get current authenticated user info (requires Authorization header).

**Headers:** `Authorization: Bearer {token}`

**Response:**
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "created_at": "2024-01-15T10:30:00"
}
```

### Classification Endpoints

#### POST /classify
Classify an email as phishing, spam, or legitimate.

**Request:**
```json
{
  "email_text": "Full email content here..."
}
```

**Response:**
```json
{
  "label": "LEGITIMATE",
  "confidence": 0.95,
  "reasoning": "This email appears to be a genuine business communication...",
  "latency_ms": 1250.5,
  "tokens_used": 450
}
```

**Note:** Optional authentication. If authenticated, classification is linked to user.

#### POST /classify-batch
Classify multiple emails in a single request.

**Request:**
```json
{
  "emails": [
    "Email content 1...",
    "Email content 2...",
    "Email content 3..."
  ]
}
```

**Response:**
```json
{
  "total": 3,
  "results": [
    {"success": true, "data": { /* classification result */ }},
    {"success": true, "data": { /* classification result */ }},
    {"success": false, "error": "Error message"}
  ]
}
```

### Metrics & Analytics Endpoints

#### GET /metrics
Get aggregated statistics from classifications (optionally filtered by user).

**Query Parameters:**
- None (returns all-time stats or user-specific if authenticated)

**Response:**
```json
{
  "total_calls": 42,
  "average_latency_ms": 1287.34,
  "error_rate": 2.38,
  "total_tokens_used": 18900,
  "estimated_cost": 0.0378
}
```

#### GET /history
Get the last 50 classification results with optional filtering.

**Query Parameters:**
- `label` (optional): Filter by label (PHISHING, SPAM, LEGITIMATE, or ALL)
- `search` (optional): Search in email snippets

**Response:**
```json
[
  {
    "timestamp": "2024-01-15T14:30:45",
    "label": "PHISHING",
    "confidence": 0.92,
    "email_snippet": "Click here to verify your account: https://malicious.com..."
  }
]
```

#### GET /analytics
Get advanced analytics including distribution and trends.

**Response:**
```json
{
  "distribution": {
    "PHISHING": 12,
    "SPAM": 25,
    "LEGITIMATE": 105
  },
  "trends": [
    {
      "time": "2024-01-15 10:00",
      "count": 15,
      "avg_confidence": 0.87
    }
  ],
  "top_hours": [
    {"time": "2024-01-15 14:00", "count": 25}
  ]
}
```

## Frontend Features

### Dashboard Tab
- **Metric Cards**: Total calls, average latency, error rate, estimated cost
- **Latency Chart**: Line chart showing latency trend over the last 20 calls
- **Auto-refresh**: Metrics update every 10 seconds
- **Per-user data**: If logged in, shows only your classifications

### Email Classifier Tab
- **Input Textarea**: Paste full email content (headers + body)
- **Classification Result**: Shows threat label (color-coded), confidence with progress bar, and reasoning
- **Performance Metrics**: Processing time and tokens used
- **History Table**: Latest 10 classifications with filter and search
  - Filter by threat label (Phishing, Spam, Legitimate)
  - Search by email content
  - Real-time filtering

### Batch Classifier Tab (NEW)
- **Multiple Input Methods**:
  - Upload CSV or text files
  - Paste multiple emails (one per line)
- **Batch Processing**: Process up to 50 emails at once
- **Results Summary**: 
  - Success/failure count
  - Distribution breakdown (phishing/spam/legitimate)
  - Average confidence score
- **Detailed Results Table**: See individual classification results with status

### Analytics Tab (NEW)
- **Distribution Chart**: Pie chart of threat classification distribution
- **Trend Chart**: 24-hour classification trends with volume and confidence
- **Peak Hours**: Bar chart showing busiest classification times
- **Summary Statistics**: Breakdown of each threat category with percentages

### Dark Mode
- Toggle button in the header
- Theme persists across sessions
- All UI elements adapt to dark mode

### Authentication
- **Login/Register**: Access from the landing page
- **Session Management**: 
  - Automatic token storage and validation
  - One-click logout
  - User info display in header
- **Data Privacy**: Classifications are private per user

## How It Works

1. **Email Classification Flow**:
   - User pastes email into the classifier
   - Frontend sends POST request to `/classify`
   - Backend sends email to LLM with classification prompt
   - LLM returns label, confidence, and reasoning
   - Results are logged to SQLite database
   - Response returned to frontend with latency and token count

2. **Monitoring**:
   - Every LLM call is automatically logged with timestamp, latency, tokens, and success status
   - Dashboard aggregates this data for real-time metrics
   - Cost is estimated based on token usage

3. **Real-time Updates**:
   - Dashboard polls `/metrics` every 10 seconds
   - Chart updates with new latency data points
   - Shows live view of system performance

## Database Schema

### classification_logs table
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| timestamp | DateTime | When the classification occurred |
| email_snippet | String | First 200 chars of email for reference |
| label | String | PHISHING, SPAM, or LEGITIMATE |
| confidence | Float | Confidence score 0.0-1.0 |
| reasoning | String | LLM's explanation |
| latency_ms | Float | Processing time in milliseconds |
| tokens_used | Integer | Total tokens consumed |
| success | Boolean | Whether the call succeeded |
| error_message | String | Error details if failed |

## Environment Variables

### Backend (.env)
- `OPENAI_API_KEY`: Your API key for LiteLLM proxy
- `LITELLM_BASE_URL`: Base URL of the LiteLLM proxy (default: https://api.ai.it.ufl.edu)

## Cost Estimation

The system estimates costs based on the model and token usage:
- Model: gpt-3.5-turbo
- Cost: $0.002 per 1,000 tokens
- Total Cost = (Total Tokens / 1000) * 0.002

## Troubleshooting

### Backend Connection Error
- Ensure the FastAPI server is running on `http://localhost:8000`
- Check that the .env file is properly configured

### LLM API Errors
- Verify your `OPENAI_API_KEY` is correct
- Ensure the LiteLLM proxy at `https://api.ai.it.ufl.edu` is accessible
- Check network connectivity and firewall rules

### Database Issues
- Delete `sentinel.db` to reset the database
- Ensure you have write permissions in the backend directory

### Frontend Not Loading Data
- Open browser DevTools to check for CORS errors
- Verify the backend server is running and accessible
- Check that the API_BASE_URL in components matches your backend URL

## Development Notes

- The frontend uses Vite for fast development and builds
- Tailwind CSS is used for all styling (no component libraries)
- Recharts is used for the latency trend chart
- SQLite is used for simplicity; can be migrated to PostgreSQL for production
- CORS is enabled for all origins; restrict in production

## Future Enhancements

- Support for multiple LLM models and providers
- Advanced filtering and search in history
- Custom classification prompts per organization
- User authentication and role-based access control
- Bulk email classification from CSV files
- Advanced analytics and reporting dashboard
- Webhook support for real-time alerts
- Model performance comparison tools
