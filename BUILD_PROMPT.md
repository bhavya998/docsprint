# MASTER BUILD PROMPT — DocSprint SaaS

## IDENTITY
You are a senior full-stack engineer building a production SaaS product called **DocSprint**. This is a real product, not a demo. Write production-quality code with proper error handling, type hints, docstrings, and tests.

## WHAT YOU'RE BUILDING
An AI document processing SaaS where:
1. Users sign up and get an API key
2. They upload documents (PDF, PNG, JPG) via web dashboard or REST API
3. The system processes each document through a vision-language model (Qwen3.5-0.8B) running on a local GPU
4. Users get back structured JSON (extracted text, descriptions, or Q&A)
5. Usage is tracked per-page for billing

## ARCHITECTURE
```
Next.js Dashboard (port 3000)
    → FastAPI Gateway (port 8000) — auth, rate limiting, file upload
    → Redis Queue (port 6379) — async job processing
    → RQ Worker — loads VL model on GPU, processes documents
    → PostgreSQL (port 5432) — users, documents, jobs, usage
```

## FILE STRUCTURE — CREATE ALL OF THESE

### Backend (`src/docsprint/`)

```
src/docsprint/
├── __init__.py
├── main.py                    # FastAPI app factory, CORS, router registration
├── cli.py                     # Typer CLI (server, worker, migrate commands)
├── config.py                  # Pydantic Settings — reads from .env
├── database.py                # SQLAlchemy engine + session factory
│
├── core/
│   ├── __init__.py
│   ├── security.py            # JWT token create/verify, password hash/verify (bcrypt)
│   ├── dependencies.py        # FastAPI deps: get_current_user, get_db, rate_limit
│   └── exceptions.py          # Custom exceptions + handlers
│
├── models/
│   ├── __init__.py
│   ├── user.py                # User: id, email, hashed_password, plan, api_key, created_at
│   ├── document.py            # Document: id, user_id, filename, status, page_count, created_at
│   ├── job.py                 # Job: id, document_id, status, result_json, error, processing_time
│   └── usage.py               # UsageRecord: id, user_id, pages_processed, month, year
│
├── api/
│   ├── __init__.py
│   ├── router.py              # Main router — includes all sub-routers
│   ├── auth.py                # POST /auth/register, POST /auth/login, GET /auth/me
│   ├── documents.py           # POST /documents/upload, GET /documents, GET /documents/{id}
│   ├── jobs.py                # GET /jobs, GET /jobs/{id}, GET /documents/{id}/result
│   └── usage.py               # GET /usage, GET /usage/current-period
│
├── services/
│   ├── __init__.py
│   ├── document_service.py    # File upload handling, validation, storage
│   ├── job_service.py         # Create jobs, enqueue to Redis, check status
│   ├── usage_service.py       # Track page usage, check quotas, reset monthly
│   └── model_service.py       # VL model loader + inference (wraps Qwen3.5-0.8B)
│
└── workers/
    ├── __init__.py
    └── inference_worker.py    # RQ worker function: receives job, runs model, saves result
```

### Frontend (`ui/src/`)

```
ui/src/
├── app/
│   ├── layout.tsx             # Root layout with auth provider
│   ├── page.tsx               # Landing page (hero + features + pricing)
│   ├── globals.css            # Tailwind 4 theme (dark mode)
│   ├── login/page.tsx         # Login form
│   ├── register/page.tsx      # Registration form
│   ├── dashboard/
│   │   ├── layout.tsx         # Dashboard layout with sidebar
│   │   ├── page.tsx           # Overview: usage stats, recent documents
│   │   ├── documents/page.tsx # Upload + document list + results viewer
│   │   ├── api-keys/page.tsx  # API key management
│   │   └── settings/page.tsx  # Account settings, plan info
│   └── docs/
│       └── page.tsx           # API documentation (endpoints, examples)
│
├── components/
│   ├── ui/                    # Reusable UI: Button, Card, Input, Badge, Table
│   ├── FileUpload.tsx         # Drag-drop upload component with progress
│   ├── JobStatus.tsx          # Real-time job status polling
│   ├── ResultViewer.tsx       # JSON result display with syntax highlighting
│   ├── UsageBar.tsx           # Usage meter (X / Y pages used)
│   └── Sidebar.tsx            # Dashboard navigation
│
└── lib/
    ├── api.ts                 # API client (fetch wrapper, auth token handling)
    ├── auth.tsx               # Auth context provider (React context)
    └── types.ts               # TypeScript types matching backend models
```

### Database Migrations (`alembic/`)

```
alembic/
├── env.py                     # Alembic env — imports all models, uses DATABASE_URL
├── versions/
│   └── 001_initial.py         # Creates: users, documents, jobs, usage_records tables
```

### Tests (`tests/`)

```
tests/
├── __init__.py
├── conftest.py                # Fixtures: test DB, test client, mock model
├── test_auth.py               # Register, login, token validation
├── test_documents.py          # Upload, list, get, delete
├── test_jobs.py               # Job creation, status polling, results
├── test_usage.py              # Quota enforcement, usage tracking
└── test_api.py                # Full API integration with TestClient
```

## API SPECIFICATION

### Auth
```
POST /api/v1/auth/register
  Body: { "email": "...", "password": "..." }
  Returns: { "access_token": "...", "token_type": "bearer", "user": {...} }

POST /api/v1/auth/login
  Body: { "email": "...", "password": "..." }
  Returns: { "access_token": "...", "token_type": "bearer", "user": {...} }

GET /api/v1/auth/me
  Headers: Authorization: Bearer <token>
  Returns: { "id": ..., "email": "...", "plan": "free", "api_key": "..." }
```

### Documents
```
POST /api/v1/documents/upload
  Headers: Authorization: Bearer <token>
  Body: multipart form — file (UploadFile), mode ("extract" | "describe" | "ask"), prompt/question (optional)
  Returns: { "document_id": ..., "job_id": ..., "status": "queued" }
  Side effect: enqueues RQ job, deducts page count from usage quota

GET /api/v1/documents
  Returns: [ { "id": ..., "filename": "...", "status": "...", "created_at": "...", "page_count": ... }, ... ]

GET /api/v1/documents/{id}
  Returns: { "id": ..., "filename": "...", "status": "completed", "result": {...}, ... }
```

### Jobs
```
GET /api/v1/jobs/{id}
  Returns: { "id": ..., "status": "processing", "progress": 50, "result": null }

GET /api/v1/documents/{id}/result
  Returns: { "pages": [ { "page": 1, "content": "...", "has_extracted_text": true } ], "format": "pdf" }
```

### Usage
```
GET /api/v1/usage
  Returns: { "plan": "free", "pages_used": 7, "pages_limit": 10, "period": "2026-07" }
```

### API Key Access (for programmatic access)
```
POST /api/v1/documents/upload   (same as above but with Header: X-API-Key: dsk_...)
```

## DATABASE SCHEMA

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    plan VARCHAR(20) DEFAULT 'free',          -- free, starter, pro
    api_key VARCHAR(64) UNIQUE NOT NULL,      -- dsk_<random>
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_format VARCHAR(10) NOT NULL,         -- pdf, png, jpg
    page_count INTEGER DEFAULT 0,
    mode VARCHAR(20) DEFAULT 'extract',       -- extract, describe, ask
    status VARCHAR(20) DEFAULT 'queued',      -- queued, processing, completed, failed
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'queued',
    result_json TEXT,                          -- JSON result from model
    error TEXT,
    processing_time_seconds FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE usage_records (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    pages_processed INTEGER DEFAULT 0,
    month INTEGER NOT NULL,
    year INTEGER NOT NULL,
    UNIQUE(user_id, month, year)
);
```

## MODEL SERVICE (GPU Worker)

The worker wraps the mmdoc VL model (Qwen3.5-0.8B). Copy the proven pattern from the mmdoc project:

```python
# src/docsprint/services/model_service.py
# This runs INSIDE the RQ worker process (not the API server)

class VLModelService:
    """Loads Qwen3.5-0.8B in 4-bit on GPU, provides extract/describe/ask."""

    def __init__(self, model_id: str = "Qwen/Qwen3.5-0.8B"):
        self._model_id = model_id
        self._model = None
        self._processor = None

    def _load(self):
        # CRITICAL: Use Qwen3_5ForConditionalGeneration, NOT Qwen3VLForConditionalGeneration
        # The model architecture is qwen3_5, not qwen3_vl
        from transformers import Qwen3_5ForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
        import torch
        # ... 4-bit loading, same as mmdoc

    def process_document(self, file_path: str, mode: str, prompt: str) -> dict:
        # Returns structured result based on mode
        # mode="extract" → { "pages": [{ "page": 1, "content": "...", ... }] }
        # mode="describe" → { "description": "..." }
        # mode="ask" → { "answer": "..." }
```

**IMPORTANT:** The model uses `Qwen3_5ForConditionalGeneration` class (NOT `Qwen3VLForConditionalGeneration`). This was a critical bug in the original mmdoc project. The model architecture is `qwen3_5` (hybrid linear+full attention VL model), not `qwen3_vl`.

## CONFIGURATION

### Backend `.env`
```
DATABASE_URL=postgresql+psycopg2://docsprint:docsprint@localhost:5432/docsprint
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=<openssl-rand-hex-32>
ACCESS_TOKEN_EXPIRE_MINUTES=10080
UPLOAD_DIR=./data/uploads
RESULT_DIR=./data/results
MAX_FILE_SIZE_MB=20
FREE_TIER_PAGES=10
MODEL_ID=Qwen/Qwen3.5-0.8B
CORS_ORIGINS=http://localhost:3000
```

### Frontend `.env.local`
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## BUILD ORDER (follow this sequence)

### Phase 1: Backend Foundation (do this first)
1. `config.py` — Pydantic Settings
2. `database.py` — SQLAlchemy engine + session
3. `models/` — All 4 models (User, Document, Job, UsageRecord)
4. `alembic/` — Initial migration
5. `core/security.py` — JWT + password hashing
6. `core/dependencies.py` — get_current_user, get_db

### Phase 2: API Routes
7. `api/auth.py` — Register, Login, Me
8. `api/documents.py` — Upload, List, Get
9. `api/jobs.py` — Job status, results
10. `api/usage.py` — Usage tracking, quota check
11. `main.py` — App factory, wire everything together

### Phase 3: Job Processing
12. `services/document_service.py` — File handling
13. `services/job_service.py` — Redis enqueue/dequeue
14. `services/usage_service.py` — Page counting, quota enforcement
15. `services/model_service.py` — VL model wrapper
16. `workers/inference_worker.py` — RQ worker function

### Phase 4: Frontend
17. `lib/api.ts` + `lib/types.ts` — API client
18. `lib/auth.tsx` — Auth context
19. Landing page + auth pages (login/register)
20. Dashboard layout + sidebar
21. Documents page (upload + list + results)
22. API keys page
23. Usage/settings page

### Phase 5: Tests + Polish
24. `tests/` — Auth, documents, jobs, usage, API integration
25. Docker compose test (all services up)
26. README with setup instructions

## CODE STANDARDS

- Python 3.12+, type hints on every function, docstrings on every public function
- Pydantic v2 for all schemas and settings
- SQLAlchemy 2.0 style (Mapped, mapped_column)
- FastAPI async routes where possible (sync for GPU operations)
- Next.js 16 App Router, React 19, Tailwind 4
- All API endpoints under `/api/v1/` prefix
- JWT bearer token auth, API key alt auth via `X-API-Key` header
- Rate limiting: 100 req/min for free tier, 1000/min for paid
- File upload max: 20MB, formats: PDF, PNG, JPG, GIF, TIFF, BMP, WebP

## DOCKER COMPOSE — must work with single command

```bash
docker-compose up -d    # starts postgres, redis, api, worker
cd ui && npm run dev    # starts frontend
```

## SUCCESS CRITERIA

A user should be able to:
1. Register at `localhost:3000/register`
2. Upload a PDF invoice
3. See job status change: queued → processing → completed
4. View extracted JSON result in the dashboard
5. See usage meter update (7/10 pages used)
6. Copy their API key and use it programmatically:
   ```bash
   curl -X POST http://localhost:8000/api/v1/documents/upload \
     -H "X-API-Key: dsk_..." \
     -F "file=@invoice.pdf" \
     -F "mode=extract"
   ```

## NOTES FOR THE AI AGENT

- This is a REAL SaaS product, not a demo. Write production code.
- The VL model integration is proven (mmdoc project works with 100% accuracy on PDFs)
- Use `Qwen3_5ForConditionalGeneration` — not `Qwen3VLForConditionalGeneration`
- PyTorch CUDA index is already configured in pyproject.toml
- Docker compose must bring up: postgres, redis, api, worker
- Frontend runs separately (npm run dev) for hot reload during development
- Add `.env` from `.env.example` before running anything
- Run `alembic upgrade head` before starting the API
- The worker is a separate process: `rq worker doc-processing --url redis://localhost:6379/0`
