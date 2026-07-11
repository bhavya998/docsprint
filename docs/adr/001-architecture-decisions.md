# ADR 001: Architecture Decisions for DocSprint

## Status
Accepted

## Context
DocSprint is an AI document processing SaaS that needs to handle file uploads, queue GPU-intensive vision-language model inference, track usage for billing, and provide both a web dashboard and REST API.

## Decisions

### 1. RQ (Redis Queue) over Celery
**Decision:** Use RQ for job queueing.

**Rationale:**
- RQ is lighter weight (~200 LOC core vs Celery's ~20K)
- Single concern: enqueue Python functions, nothing more
- Works with Redis which we already need for rate limiting
- No broker protocol to configure (Celery requires RabbitMQ or Redis with complex routing)
- Perfect for our pattern: API enqueues → worker picks up → updates DB

**Trade-offs:**
- No built-in task scheduling (CRON) — not needed, jobs run immediately
- No multi-broker support — we only need Redis
- Less community plugins — we don't need any

### 2. JWT + API Key Dual Auth
**Decision:** Support both `Authorization: Bearer <JWT>` and `X-API-Key: dsk_...`

**Rationale:**
- Web dashboard uses JWT (browser-friendly, short-lived)
- API consumers use API keys (simple, no token refresh needed)
- Both map to the same user identity
- API keys have `dsk_` prefix for easy identification in logs

**Trade-offs:**
- Two code paths to maintain in auth dependencies
- API keys are long-lived (mitigated by user-specific, easily rotatable)

### 3. Sync SQLAlchemy (not async)
**Decision:** Use synchronous SQLAlchemy 2.0 with `Mapped`/`mapped_column`.

**Rationale:**
- FastAPI runs sync endpoint functions in thread pools efficiently
- GPU model inference is sync anyway (can't async a GPU)
- Simplify database session management (no `async with` everywhere)
- SQLAlchemy 2.0 style provides type safety without the async complexity

**Trade-offs:**
- Cannot use asyncpg for PostgreSQL connection pooling
- Higher latency under extreme concurrency (mitigated by thread pool)

### 4. Qwen3.5-0.8B in 4-bit quantization
**Decision:** Use `Qwen3_5ForConditionalGeneration` (NOT `Qwen3VLForConditionalGeneration`) with BitsAndBytes 4-bit.

**Rationale:**
- `qwen3_5` architecture supports both text and vision (unified multimodal)
- `qwen3_vl` was the incorrect architecture that broke the original mmdoc project
- 4-bit quantization fits the 0.8B model into ~1GB VRAM
- Runs on consumer GPUs (RTX 3060+)

**Trade-offs:**
- 4-bit has minor accuracy loss vs fp16 (acceptable for extraction)
- Not all CUDA GPUs support 4-bit (requires compute capability 7.0+)

### 5. DEV_MODE for No-Infra Development
**Decision:** `DEV_MODE=true` processes documents synchronously on upload, bypassing Redis/RQ.

**Rationale:**
- Developers without Docker/Redis can still use the full product
- GPU model loads once and processes inline
- Useful for quick demos and testing
- Production deployments set `DEV_MODE=false` to use the queue

**Trade-offs:**
- Upload endpoints block during processing (seconds-minutes on GPU)
- No retry mechanism on failure in sync mode

### 6. In-Memory Rate Limiting (with Redis path reserved)
**Decision:** Default rate limiter uses in-memory sliding window. Redis-based limiter is a future upgrade.

**Rationale:**
- Works without Redis (DEV_MODE friendly)
- Sliding window algorithm is simple and effective
- Per-plan limits (free: 100/min, pro: 1000/min)
- Easy to swap to Redis sliding window for multi-process deployments

**Trade-offs:**
- Not shared across multiple API processes (needs sticky sessions or Redis)
- Resets on server restart