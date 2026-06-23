# ATS Checker Personal

A complete, production-quality **local ATS Resume Checker** for personal use. No cloud, no paid APIs, 100% runs on your machine.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, TypeScript, TailwindCSS, Shadcn UI, Recharts |
| Backend | FastAPI, Python 3.12, SQLite |
| NLP | spaCy (en_core_web_sm), sentence-transformers (all-MiniLM-L6-v2) |
| Matching | scikit-learn TF-IDF, rapidfuzz fuzzy matching |
| File Parsing | PyMuPDF (PDF), python-docx (DOCX) |
| Export | ReportLab (PDF), Python CSV |

## Prerequisites

- Python 3.12+
- Node.js 18+
- ~500MB free disk space (for NLP models)

## Quick Start

### 1. Setup (run once)

```bat
setup.bat
```

This will:
- Create Python virtual environment
- Install all Python packages
- Download spaCy model (~12MB)
- Download sentence-transformer model (~80MB)
- Install Node.js packages

### 2. Start the Application

```bat
start.bat
```

This opens:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## ATS Scoring Engine

### Weighted Scoring

| Category | Weight | Method |
|----------|--------|--------|
| Keyword Match | 35% | TF-IDF extraction + exact/fuzzy match (rapidfuzz) |
| Skills Match | 25% | 200+ tech skills taxonomy + alias normalization |
| Experience Match | 15% | Years extraction from dates + regex patterns |
| Education Match | 10% | Degree level detection (Bachelor=3, Master=4, PhD=5) |
| Semantic Similarity | 15% | all-MiniLM-L6-v2 sentence embeddings + cosine similarity |

### Score Interpretation

| Score | Meaning |
|-------|---------|
| 75–100 | Excellent — Strong match |
| 60–74 | Good — Solid candidate |
| 45–59 | Fair — Some gaps |
| 0–44 | Needs Work — Significant gaps |

## Features

### Resume Analysis
- Drag & drop upload for PDF and DOCX
- Multiple resume upload
- Extract: name, email, phone, LinkedIn, GitHub, skills, education, experience, projects, certifications
- Section detection (Experience, Education, Skills, Projects, etc.)

### ATS Scoring
- Overall ATS Score (0–100)
- 5-dimension breakdown with weighted scoring
- Radar chart visualization
- Keyword match with fuzzy matching
- Skills match with 200+ skills taxonomy

### Missing Keywords Detection
- Missing critical keywords from JD
- Missing required skills
- Matched vs unmatched analysis

### Improvement Suggestions
- Skills to add
- Keywords to include
- Missing sections
- Formatting and ATS optimization tips
- Quantifiable achievement recommendations

### Candidate Ranking (Bulk Mode)
- Run analysis for multiple resumes at once
- Automatic ranking by ATS score
- Sortable columns (rank, keyword, skills, semantic score)
- Export rankings to CSV

### Export
- PDF report per analysis (via ReportLab)
- CSV ranking export

### History
- All previous analyses stored in SQLite
- Search and filter by date
- Delete unwanted analyses

## Project Structure

```
ats-checker-personal/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── config.py            # Settings and configuration
│   │   ├── models/
│   │   │   ├── database.py      # SQLAlchemy ORM models
│   │   │   └── schemas.py       # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── resumes.py       # Resume upload & management
│   │   │   ├── job_descriptions.py  # JD CRUD
│   │   │   ├── analysis.py      # ATS analysis & dashboard
│   │   │   ├── rankings.py      # Candidate rankings
│   │   │   └── exports.py       # PDF/CSV export
│   │   ├── services/
│   │   │   ├── nlp_engine.py    # spaCy + sentence-transformers
│   │   │   ├── resume_parser.py # PDF/DOCX parsing & extraction
│   │   │   ├── ats_scorer.py    # ATS scoring algorithm
│   │   │   └── export_service.py # Report generation
│   │   └── utils/
│   │       └── helpers.py       # Text utilities (email, phone, sections)
│   ├── tests/
│   │   ├── test_resume_parser.py
│   │   ├── test_ats_scorer.py
│   │   └── test_api.py
│   ├── data/                    # SQLite DB + uploads (auto-created)
│   ├── requirements.txt
│   └── setup_nlp.py
├── frontend/
│   ├── app/
│   │   ├── dashboard/page.tsx   # Dashboard with stats & charts
│   │   ├── analysis/page.tsx    # Resume analysis workflow
│   │   ├── ranking/page.tsx     # Candidate ranking table
│   │   ├── history/page.tsx     # Analysis history
│   │   └── settings/page.tsx    # Data management
│   ├── components/
│   │   ├── ui/                  # Shadcn UI components
│   │   └── custom/              # App-specific components
│   └── lib/
│       ├── api.ts               # API client
│       └── utils.ts             # Utilities
├── setup.bat                    # One-time setup
├── start.bat                    # Start application
└── run_tests.bat                # Run test suite
```

## Running Tests

```bat
run_tests.bat
```

Or manually:
```bash
cd backend
venv\Scripts\activate
pytest tests/ -v
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/health | Health check |
| POST | /api/resumes/upload | Upload resume(s) |
| GET | /api/resumes | List all resumes |
| DELETE | /api/resumes/{id} | Delete resume |
| POST | /api/job-descriptions | Create/save JD |
| GET | /api/job-descriptions | List JDs |
| POST | /api/analysis/run | Run single analysis |
| POST | /api/analysis/bulk | Run bulk analysis |
| GET | /api/analysis/dashboard | Dashboard stats |
| GET | /api/rankings/{jd_id} | Get rankings for JD |
| GET | /api/exports/pdf/{analysis_id} | Export PDF report |
| GET | /api/exports/csv/{jd_id} | Export CSV rankings |

## Performance

- Resume parsing: ~1–2 seconds
- ATS scoring: ~2–5 seconds (3–4s for semantic similarity on first load)
- Model warm-up: ~5 seconds (first analysis only)
- Supports 100+ resumes

## Limitations

- Semantic similarity uses CPU (no GPU required, but GPU would be faster)
- PDF parsing may struggle with heavily formatted or image-based PDFs
- Skills taxonomy covers ~200 tech skills; niche/domain-specific skills may be missed
- Experience years extraction depends on standard date formats in resumes
