<div align="center">

# docsprint

**Document processing as a multi-tenant service: upload a PDF or image, get structured JSON back. Accounts, API keys, an async GPU job queue, usage metering and plan limits around a local 0.8B vision-language model.**

[![CI](https://github.com/bhavya998/docsprint/actions/workflows/ci.yml/badge.svg)](https://github.com/bhavya998/docsprint/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=next.js&logoColor=white)](https://nextjs.org)
[![License](https://img.shields.io/badge/License-MIT-22c55e)](LICENSE)

</div>

---

## What this is

[mmdoc](https://github.com/bhavya998/mmdoc) answers "can a 0.8B vision-language model read
invoices and forms well enough?" — a library, CLI and single-user UI. docsprint answers the next
question: **what does it take to run that model as a product for many users?**

- **Accounts and two auth paths** — JWT for the dashboard, `X-API-Key: dsk_…` for programmatic use; both resolve to the same user
- **Async inference** — uploads return immediately; a Redis/RQ worker owns the GPU and loads the model once per process
- **Usage metering and plans** — pages counted at upload, per-plan monthly quotas (free / starter / pro), usage history endpoint
- **Rate limiting** — sliding-window limits per plan on every API route
- **Postgres + Alembic** — users, documents, jobs and usage records with migrations
- **Dashboard** — Next.js 16 app for upload, job status, results, API keys and usage
- **DEV_MODE** — processes synchronously with no Redis, for local work and tests

## Architecture

```
 Next.js dashboard ──JWT──┐
                          ▼
 API clients ──X-API-Key──► FastAPI /api/v1 ── rate limit ── quota check
                                  │
                     store file, create Document + Job, meter pages
                                  │
                                  ▼
                         Redis queue (RQ)  ──►  GPU worker
                                                  Qwen3.5-0.8B, 4-bit, ~1 GB VRAM
                                                  extract · describe · ask
                                  ▲                     │
                                  └──── PostgreSQL ◄────┘
                            users · documents · jobs · usage
```

Design decisions (RQ over Celery, dual auth, sync SQLAlchemy, model architecture) are recorded in
[`docs/adr/001-architecture-decisions.md`](docs/adr/001-architecture-decisions.md).

## Quick start

```bash
git clone https://github.com/bhavya998/docsprint.git
cd docsprint
cp .env.example .env

# Full stack: postgres, redis, api (runs migrations on start), worker
docker compose up -d
cd ui && npm install && npm run dev      # dashboard on http://localhost:3000

# Or without Docker: SQLite + synchronous processing on the local GPU
export DEV_MODE=true DATABASE_URL=sqlite:///./data/docsprint.db
mkdir -p data && uv run alembic upgrade head
uv run docsprint server
```

The model (~2 GB) downloads from Hugging Face on the first job. The compose worker has no GPU
reservation, so it runs on CPU; add a `deploy.resources.reservations.devices` entry (NVIDIA
Container Toolkit) to give it the GPU.

## API

All routes are under `/api/v1`. Interactive docs at `/docs`.

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/auth/register` | Create an account; returns a JWT and a `dsk_` API key |
| `POST` | `/auth/login` | Exchange email + password for a JWT |
| `GET` | `/auth/me` | Current user and plan |
| `POST` | `/documents/upload` | Upload a file with `mode` = `extract` \| `describe` \| `ask` (+ optional `prompt`) |
| `GET` | `/documents` | List your documents |
| `GET` | `/documents/{id}` | Document detail |
| `GET` | `/documents/{id}/result` | Structured result once the job finishes |
| `GET` | `/jobs`, `/jobs/{id}` | Job status: `queued` → `processing` → `completed` / `failed` |
| `GET` | `/usage`, `/usage/history` | Pages used against the plan quota |

```bash
curl -H "X-API-Key: dsk_..." -F "file=@invoice.pdf" -F "mode=extract" \
  http://localhost:8000/api/v1/documents/upload
```

## Testing

```bash
uv run pytest -v          # auth, documents, jobs, usage, API, and a live-server e2e suite
uv run ruff check src tests
```

The end-to-end suite starts a real uvicorn server on SQLite, runs the migrations and exercises
every endpoint over HTTP. CI runs the backend tests, the frontend build and the Docker build.

## Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI, Pydantic v2, python-jose (JWT), passlib/bcrypt |
| Data | PostgreSQL 16, SQLAlchemy 2.0, Alembic |
| Queue | Redis 7 + RQ |
| Model | Qwen3.5-0.8B (unified vision-language), transformers + bitsandbytes 4-bit |
| Documents | PyMuPDF, Pillow |
| Frontend | Next.js 16, React 19, Tailwind 4 |
| Packaging | uv, Docker Compose |

## Status and limitations

- Billing is metered but not charged: plans and quotas exist, Stripe is not wired in.
- Files are stored on the local filesystem; object storage (S3) is not implemented.
- The rate limiter is in-memory, so limits hold per API process, not across replicas.
- One GPU worker processes jobs in order; scaling out means more workers on more GPUs.

[SPEC.md](SPEC.md) has the product brief.

## License

MIT
