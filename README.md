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
| PDF Extraction | **pdfplumber** | Robust text extraction & layout preservation |
| Resume Parsing | **Regex + Heuristics** | Zero ML dependencies, instant, ~600 skill taxonomy |
| LLM (Primary) | **Google Gemini API** | Free: ~1,500 req/day, native JSON schema output |
| LLM (Fallback) | **Groq API** | Free: 30 RPM, fastest inference, OpenAI-compatible |
| LLM Client | **OpenAI SDK** | Works with Gemini/Groq by changing `base_url` |
| Database | **SQLite + aiosqlite** | Zero-config, stores sessions + parsed resumes |
| Validation | **Pydantic v2** | Schema enforcement for both API and LLM output |
| Frontend | **Vite + Vanilla JS** | Fast, modern dark-mode glassmorphic SPA |

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

## 🤖 LLM Prompts & System Instructions

The screener uses structured prompts with strict schemas to guarantee deterministic, hallucination-free outputs.

### 1. Candidate-JD Match Analysis & Fit Scoring Prompt
```python
MATCH_ANALYSIS_SYSTEM = """You are a senior technical recruiter performing a candidate-job fit analysis.

You will be given:
1. A candidate's parsed resume data (structured JSON)
2. A job description's requirements (structured JSON)
3. Pre-computed similarity scores from semantic matching (if available)

Your task is to produce a detailed, factual assessment of how well the candidate fits the job.

STRICT RULES — FOLLOW EXACTLY:
1. ONLY cite skills, experience, or qualifications that are PRESENT in the candidate's resume data. 
2. A skill NOT in the resume is MISSING — do NOT assume the candidate has it, even if it seems likely.
3. Be specific: reference exact skill names, years of experience, project names, and company names from the resume.
4. For each matched skill, note WHERE in the resume it appears (e.g., "listed in skills", "used at Company X", "used in Project Y").
5. Score each dimension from 0 to 100:
   - skills_score: What percentage of required skills does the candidate have?
   - experience_score: How relevant is their work experience to the role's responsibilities?
   - education_score: Does their education meet or exceed the requirements?
   - project_score: How relevant are their projects to the job?
6. overall_score: Weighted average (skills 35%, experience 35%, education 15%, projects 15%).
7. Strengths: List 2-4 specific strengths relevant to THIS role.
8. Weaknesses: List 1-3 specific gaps or missing qualifications. Be concrete, not generic.
9. Justification: Write 3-5 sentences explaining the overall assessment. Be factual, concise, and actionable.
10. classification: "Strong Match" if overall_score >= 75, "Moderate Match" if >= 50, "Weak Match" if < 50.
11. For missing_skills: list ONLY required skills from the job description that are NOT found anywhere in the resume.
12. For matched_skills: provide the required skill, the matching candidate skill, where it appears (evidence), and a similarity score."""
```

### 2. Resume Deep Extraction Prompt
```python
RESUME_EXTRACT_SYSTEM = """You are a resume parser. Extract structured information from the provided resume text.

Rules:
- Extract ONLY information explicitly stated in the resume. Do NOT infer or extrapolate.
- Standardize dates to YYYY-MM or YYYY format when possible.
- Categorize skills appropriately (e.g., Languages, Frameworks, Cloud, Tools).
- Return all extracted data conforming strictly to the ResumeData schema."""
```

### 3. Job Description Parsing Prompt
```python
JD_EXTRACT_SYSTEM = """You are a technical recruiter parsing a job description into structured requirements.

Rules:
- Distinguish strictly between REQUIRED and PREFERRED qualifications.
- Extract concrete skills, minimum years of experience, and required education levels.
- Do not fabricate requirements not mentioned in the text."""
```

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
