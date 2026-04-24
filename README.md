# CareerAI Pro

AI-powered career intelligence platform. Analyzes resumes, predicts roles and salaries, surfaces live job listings, industry news, and Coursera courses — all in a single dark-themed UI.

---

## Features

| Section | Description |
|---|---|
| Dashboard | Live market overview — top skills, salary ranges, role demand |
| Resume Analyzer | ML role prediction, skill-gap analysis, resume scoring |
| Job Board | Live job search via JSearch RapidAPI with filters and bookmarks |
| Career Roadmap | Week-by-week learning paths for 12 AI/ML roles |
| Salary Predictor | Role + experience + country salary estimator |
| AI Career Chat | Groq Llama 3.3 70B chat assistant |
| Voice Interview | AI mock interviews with speech recognition |
| Industry News | Real-time headlines via NewsAPI (15-min cache) |
| Learning Courses | Coursera course catalog via RapidAPI (10-min cache) |

---

## Requirements

- Python 3.9+
- pip

---

## Quick Setup (Linux / macOS / Git Bash)

```bash
bash setup.sh
```

This will: create a virtual environment, install all dependencies, and train the ML model.

---

## Manual Setup

### 1. Clone / extract the project

```bash
cd careerai_pro_COMPLETE
```

### 2. Create and activate a virtual environment

```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate

# Windows (Command Prompt)
python -m venv venv
venv\Scripts\activate.bat

# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Train the ML model

```bash
python ml/train_model.py
```

This generates `backend/models/role_predictor.pkl`, `label_encoder.pkl`, and `model_meta.json`.  
The model achieves ~71% accuracy on 12 AI/ML role categories.

---

## Run the Server

```bash
python backend/server.py
```

Open your browser at **http://localhost:8000**

The server is also accessible on your local network at **http://\<your-ip\>:8000**

---

## API Keys

All API keys are pre-configured in the backend. The only key you need to add manually is **Groq** for AI Chat and Voice Interview features.

| Key | Where to get it | Required for |
|---|---|---|
| Groq | [console.groq.com](https://console.groq.com) (free) | AI Chat, Voice Interview |
| Sarvam AI | [dashboard.sarvam.ai](https://dashboard.sarvam.ai) (optional) | Premium voice TTS |

Enter keys in the sidebar by clicking **Connect API Keys**.

The following keys are already embedded in the backend:

| Service | Used for |
|---|---|
| RapidAPI — JSearch | Live job listings |
| RapidAPI — Coursera Courses Collection | Learning courses |
| NewsAPI | Industry news |

---

## API Endpoints

All endpoints are served by the Flask backend at `http://localhost:8000`.

```
GET  /                          Frontend (index.html)
GET  /api/health                Health check + ML model status
GET  /api/market/overview       Full market data (salaries, skills, growth)
GET  /api/market/skills         Top skills list
GET  /api/market/salary         Salary tables by role / experience / country
GET  /api/market/growth         Role growth rates and demand scores
POST /api/predict/role          ML role prediction from resume text
POST /api/predict/skill-gap     Missing skills for predicted top role
POST /api/predict/salary        Salary estimate by role + experience + country
GET  /api/model/info            ML model metadata
GET  /api/jobs/search           Live job search
GET  /api/news                  Industry news (NewsAPI proxy)
GET  /api/courses               Coursera course catalog (RapidAPI proxy)
```

### Job Search Parameters

```
GET /api/jobs/search?q=python&location=remote&job_type=fulltime&experience=mid&date_posted=week&salary_min=100000&page=1&per_page=20
```

| Parameter | Values |
|---|---|
| `q` | keyword (e.g. `python`, `machine learning`) |
| `location` | city or country |
| `remote` | `true` |
| `job_type` | `fulltime`, `parttime`, `contract`, `internship` |
| `experience` | `entry`, `mid`, `senior`, `executive` |
| `date_posted` | `today`, `3days`, `week`, `month` |
| `salary_min` | integer (USD) |
| `page` | page number |
| `per_page` | results per page (max 50) |
| `force` | `true` to bypass cache |

### News Parameters

```
GET /api/news?category=technology&pageSize=20&page=1
GET /api/news?q=artificial+intelligence&pageSize=20
```

| Parameter | Values |
|---|---|
| `category` | `technology`, `business`, `science`, `health`, `sports`, `entertainment`, `general` |
| `q` | search term (overrides category, uses `/v2/everything`) |
| `pageSize` | results per page (max 100) |
| `page` | page number |

### Courses Parameters

```
GET /api/courses?page_no=1
GET /api/courses?institution=Yale+University&page_no=1
```

| Parameter | Values |
|---|---|
| `institution` | e.g. `Yale University`, `Google`, `Stanford University`, `IBM`, `Meta` |
| `page_no` | page number (10 results per page, 622 total) |

---

## Project Structure

```
.
├── backend/
│   ├── server.py               # Flask app — all routes
│   ├── api_connectors/
│   │   ├── api_keys.py         # RapidAPI key
│   │   ├── job_service.py      # Job search orchestrator (caching, dedup, pagination)
│   │   ├── jsearch_connector.py
│   │   ├── activejobs_connector.py
│   │   └── linkedin_connector.py
│   └── models/
│       ├── role_predictor.pkl
│       ├── label_encoder.pkl
│       └── model_meta.json
├── frontend/
│   └── index.html              # Single-file frontend (vanilla JS + CSS)
├── ml/
│   └── train_model.py          # ML model training script
├── data/                       # Training data (62K+ job records)
├── requirements.txt
├── setup.sh                    # One-command setup (Linux/macOS/Git Bash)
└── README.md
```

---

## Caching

| Endpoint | TTL |
|---|---|
| `/api/jobs/search` | 5 minutes |
| `/api/news` | 15 minutes |
| `/api/courses` | 10 minutes |

Add `?force=true` (jobs) or `?_bust=<timestamp>` (news/courses via Refresh button) to bypass cache.

---

## Troubleshooting

**"No Jobs Found" error**

The backend may not be running. Make sure `python backend/server.py` is running and accessible at `http://localhost:8000/api/health`.

**ML model not found**

Run `python ml/train_model.py` to generate the model files.

**`ModuleNotFoundError`**

Make sure the virtual environment is activated before running the server.

**Port already in use**

Kill the existing process using port 8000:

```bash
# Linux / macOS
lsof -ti:8000 | xargs kill -9

# Windows
netstat -ano | findstr :8000
taskkill /F /PID <PID>
```
