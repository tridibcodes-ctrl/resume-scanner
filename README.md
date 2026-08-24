# 🔍 Smart Resume Screener

**AI-powered resume analysis and candidate ranking system** — Upload resumes and a job description, get intelligent match scores, skill analysis, and explainable justifications.

Built with zero budget using free-tier cloud LLMs and deployable for free on Render + Vercel.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Vite)                       │
│  Upload Resumes + JD  →  View Ranked Results + Details  │
└──────────────────────────┬──────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────┐
│                  Backend (FastAPI)                       │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ PyMuPDF  │→ │  Regex   │→ │   LLM    │→ │ Scorer │ │
│  │ Extract  │  │  Parser  │  │ Analyzer │  │ Ranker │ │
│  └──────────┘  └──────────┘  └────┬─────┘  └────────┘ │
│                                    │                    │
│  ┌─────────────┐  ┌───────────────▼──────────────────┐ │
│  │   SQLite    │  │  Gemini API  /  Groq API         │ │
│  │  Database   │  │  (free tier, structured JSON)    │ │
│  └─────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Processing Pipeline

1. **Text Extraction** — PyMuPDF extracts clean text from PDF/TXT resumes
2. **Regex Parsing** — Heuristic parser extracts contact info, skills (via 600+ skill taxonomy), experience, education, projects
3. **LLM Deep Extraction** — Google Gemini refines the parse with structured JSON output
4. **LLM JD Parsing** — Job description parsed into required/preferred skills, experience, education requirements
5. **LLM Match Analysis** — Candidate-JD fit analysis with scores, matched/missing skills, strengths, weaknesses, justification
6. **Ranking** — Candidates sorted by weighted overall score

---

## 🛠️ Technology Choices

| Layer | Technology | Why |
|:------|:-----------|:----|
| Backend | **FastAPI** | Async, auto-docs, Pydantic-native |
| PDF Extraction | **PyMuPDF** | 10-50x faster than alternatives, 15MB footprint |
| Resume Parsing | **Regex + Heuristics** | Zero ML dependencies, instant, ~600 skill taxonomy |
| LLM (Primary) | **Google Gemini API** | Free: ~1,500 req/day, native JSON schema output |
| LLM (Fallback) | **Groq API** | Free: 30 RPM, fastest inference, OpenAI-compatible |
| LLM Client | **OpenAI SDK** | Works with Gemini/Groq by changing `base_url` |
| Database | **SQLite + aiosqlite** | Zero-config, stores sessions + parsed resumes |
| Validation | **Pydantic v2** | Schema enforcement for both API and LLM output |
| Frontend | **Vite + Vanilla JS** | Fast, no framework bloat, serves as static SPA |

---

## 📊 Scoring Methodology

The system produces a **0-100 overall score** from weighted dimensions:

| Dimension | Weight | Method |
|:----------|:-------|:-------|
| Skills Match | 35% | Exact + semantic match of required skills |
| Experience Relevance | 35% | LLM assessment of experience-to-JD alignment |
| Education Alignment | 15% | Degree level + field relevance |
| Project Relevance | 15% | LLM assessment of project-to-JD alignment |

**Classification:**
- 🟢 **Strong Match** (≥75): Candidate meets most requirements
- 🟡 **Moderate Match** (50-74): Partial fit, notable gaps
- 🔴 **Weak Match** (<50): Significant skill/experience gaps

### Anti-Hallucination Safeguards

- LLM prompts explicitly forbid inferring skills not in the resume
- Missing skills come from `JD required - resume matched`, never from LLM invention  
- All LLM output validated against Pydantic schemas before use
- `temperature=0` for deterministic, factual responses
- Retry logic with schema validation on malformed output

---

## 🚀 Setup & Running

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** (for frontend dev server)
- At least one free LLM API key:
  - [Google AI Studio](https://aistudio.google.com/apikey) — no credit card needed
  - [Groq Console](https://console.groq.com/keys) — no credit card needed

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY and/or GROQ_API_KEY

# Start the server
uvicorn main:app --reload --port 8000
```

The API is now at `http://localhost:8000` with docs at `http://localhost:8000/docs`.

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server (proxies /api to backend)
npm run dev
```

Open `http://localhost:5173` in your browser.

### 3. Quick Test

Upload the sample resumes from `sample_data/resumes/` and paste a JD from `sample_data/job_descriptions/`. Click "Analyze" to see ranked results.

---

## 📡 API Reference

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `GET` | `/api/health` | Health check + LLM status |
| `POST` | `/api/session` | Create analysis session |
| `POST` | `/api/session/{id}/resumes` | Upload resume files |
| `POST` | `/api/session/{id}/job-description` | Submit JD text |
| `POST` | `/api/session/{id}/analyze` | Run full analysis pipeline |
| `GET` | `/api/session/{id}/results` | Get ranked results |
| `DELETE` | `/api/session/{id}` | Delete session |

### Example: cURL

```bash
# Create session
SESSION=$(curl -s -X POST http://localhost:8000/api/session | jq -r '.session_id')

# Upload resume
curl -X POST "http://localhost:8000/api/session/$SESSION/resumes" \
  -F "files=@sample_data/resumes/alice_johnson_senior_dev.txt"

# Submit JD
curl -X POST "http://localhost:8000/api/session/$SESSION/job-description" \
  -H "Content-Type: application/json" \
  -d '{"text": "Senior Software Engineer... 5+ years React, Node.js, AWS..."}'

# Analyze
curl -X POST "http://localhost:8000/api/session/$SESSION/analyze"

# Get results
curl "http://localhost:8000/api/session/$SESSION/results"
```

---

## 🤖 LLM Prompt Design

### Design Principles

1. **Anti-hallucination**: Every prompt includes "extract ONLY information explicitly stated"
2. **Structured output**: Pydantic schemas passed to LLM's `response_format` for guaranteed JSON
3. **Specificity**: Prompts require citing exact skill names, company names, project names from the resume
4. **Deterministic**: `temperature=0` eliminates creative responses
5. **Conciseness**: Justifications limited to 3-5 sentences

### Prompt Templates

See [`backend/prompts/`](backend/prompts/) for all prompt templates:
- `resume_extract.py` — Structured resume data extraction
- `jd_extract.py` — Job description requirement parsing
- `match_analysis.py` — Candidate-JD fit analysis with scoring rubric

---

## 🧪 Testing

```bash
# Run all tests from project root
cd backend && python -m pytest ../tests/ -v

# Run specific test file
python -m pytest ../tests/test_parser.py -v

# Run with coverage
python -m pytest ../tests/ -v --tb=short
```

Tests cover:
- Text extraction and normalization
- Regex-based contact info extraction (email, phone, LinkedIn, GitHub)
- Skill taxonomy matching
- Section detection (experience, education, skills, projects)
- Scoring engine (classification boundaries, weighted scoring, ranking)

---

## 📁 Project Structure

```
resume-scanner/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py             # Environment config
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── models/
│   │   ├── schemas.py        # All Pydantic models
│   │   └── database.py       # SQLite async operations
│   ├── services/
│   │   ├── extractor.py      # PDF/TXT text extraction
│   │   ├── parser.py         # Regex resume parser (600+ skill taxonomy)
│   │   ├── llm_client.py     # Provider-agnostic LLM client
│   │   └── scorer.py         # Scoring engine + LLM orchestration
│   ├── prompts/
│   │   ├── resume_extract.py # LLM prompt: resume parsing
│   │   ├── jd_extract.py     # LLM prompt: JD parsing
│   │   └── match_analysis.py # LLM prompt: match analysis
│   └── api/
│       └── routes.py         # REST API endpoints
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.js           # App logic + UI rendering
│       ├── style.css         # Full design system
│       └── api.js            # Backend API client
├── sample_data/
│   ├── resumes/              # 4 sample resumes
│   └── job_descriptions/     # 2 sample JDs
└── tests/
    ├── test_extractor.py
    ├── test_parser.py
    └── test_scorer.py
```

---

## 🌐 Deployment

### Backend → Render (Free)

1. Push to GitHub
2. Connect repo on [render.com](https://render.com)
3. Create a new **Web Service** from `backend/` directory
4. Set environment: Docker, Free plan
5. Add environment variables: `GEMINI_API_KEY`, `GROQ_API_KEY`

### Frontend → Vercel (Free)

1. Connect repo on [vercel.com](https://vercel.com)
2. Set root directory to `frontend/`
3. Set `VITE_API_URL` to your Render backend URL
4. Deploy

---

## 📄 License

MIT
