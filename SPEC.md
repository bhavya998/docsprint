# DocSprint — AI Document Processing SaaS

## Product Summary
A SaaS platform where users upload documents (PDF, images) and receive structured JSON extractions powered by a local vision-language model. Includes user authentication, async job processing, usage metering, API access, and a billing-ready architecture.

## Target Users
- **Accountants/Bookkeepers** — batch-process receipts and invoices into structured data
- **Developers** — integrate document extraction via REST API
- **Small businesses** — digitize paper forms into spreadsheets/JSON

## Competitive Landscape
| Company | Pricing |
|---|---|
| Parseur | $39-$299/mo |
| Docparser | $25-$325/mo |
| AWS Textract | $1.50/1K pages |
| Base64.ai | Enterprise |

**Our advantage:** Open-source model (no per-query API cost), documents stay on our server (privacy selling point), API-first.

## Architecture
```
User Dashboard (Next.js)
    → API Gateway (FastAPI + JWT auth + rate limiting)
    → Job Queue (Redis + RQ)
    → GPU Worker (Qwen3.5-0.8B VL model)
    → Postgres (users, documents, jobs, usage)
```

## Monetization
- **Free tier**: 10 pages/month
- **Starter**: $19/mo — 500 pages
- **Pro**: $49/mo — 2000 pages
- **API**: $0.02/page overage

## Tech Stack
| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy + Alembic |
| Frontend | Next.js 16 + React 19 + Tailwind 4 |
| Database | PostgreSQL 16 |
| Queue | Redis 7 + RQ |
| AI Model | Qwen3.5-0.8B (4-bit, local GPU) |
| Auth | JWT (python-jose) + bcrypt |
| Storage | Local filesystem (dev) / S3 (prod) |
| Billing | Stripe (phase 2) |
| Deployment | Docker Compose (dev) / cloud (prod) |

## Project Structure
```
docsprint/
├── src/docsprint/
│   ├── api/              FastAPI routes (auth, documents, jobs, billing)
│   ├── core/             Config, security (JWT), dependencies
│   ├── models/           SQLAlchemy models (User, Document, Job, UsageRecord)
│   ├── services/         Business logic (document processing, usage tracking)
│   ├── workers/          RQ workers (GPU inference pipeline)
│   └── main.py           App factory + route registration
├── ui/                   Next.js dashboard
├── alembic/              Database migrations
├── tests/                Pytest (unit + integration + API)
├── docker-compose.yml    Full stack: api, worker, postgres, redis, ui
├── Dockerfile            Backend image
├── pyproject.toml
├── Makefile
└── SPEC.md              This file
```
