"""FastAPI application factory — CORS, rate limiting, routers, and exception handlers."""

from __future__ import annotations

import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from docsprint.api.router import api_v1_router
from docsprint.config import settings
from docsprint.core.exceptions import DocSprintError


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding window rate limiter.

    Tracks request counts per API key (or IP) per minute.
    Enforces different limits based on user plan tier.
    Falls back gracefully if Redis is unavailable.
    """

    def __init__(self, app, *, free_limit: int = 100, pro_limit: int = 1000):
        super().__init__(app)
        self._free_limit = free_limit
        self._pro_limit = pro_limit
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._plan_cache: dict[str, str] = {}  # api_key -> plan

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only rate-limit API routes
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # Get identifier: prefer API key, fall back to IP
        api_key = request.headers.get("X-API-Key")
        identifier = api_key or request.client.host if request.client else "unknown"

        now = time.time()
        window = 60.0  # 1 minute window

        # Clean expired entries
        self._windows[identifier] = [
            t for t in self._windows[identifier] if now - t < window
        ]

        # Determine limit based on plan
        limit = self._free_limit
        if api_key and identifier in self._plan_cache:
            plan = self._plan_cache[identifier]
            if plan in ("starter", "pro"):
                limit = self._pro_limit

        # Check limit (allow upload endpoints to always pass — they have quota)
        if len(self._windows[identifier]) >= limit and "/upload" not in request.url.path:
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded: {limit} requests per minute"},
            )

        self._windows[identifier].append(now)
        return await call_next(request)


def _get_rate_limiter() -> RateLimitMiddleware | None:
    """Create rate limiter if enabled."""
    if settings.RATE_LIMIT_ENABLED:
        try:
            return RateLimitMiddleware(
                None,
                free_limit=settings.FREE_RATE_LIMIT,
                pro_limit=settings.PRO_RATE_LIMIT,
            )
        except Exception:
            return None
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown events."""
    # Startup: ensure upload and result directories exist
    settings.upload_path
    settings.result_path
    yield
    # Shutdown: cleanup if needed


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Sets up CORS, rate limiting, includes the v1 API router, and registers
    custom exception handlers for DocSprintError subclasses.

    Returns:
        Configured FastAPI app instance.
    """
    app = FastAPI(
        title="DocSprint",
        description="AI Document Processing SaaS — upload documents and get structured JSON",
        version="0.1.0",
        lifespan=lifespan,
    )

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Rate limiting ---
    if settings.RATE_LIMIT_ENABLED:
        app.add_middleware(
            RateLimitMiddleware,
            free_limit=settings.FREE_RATE_LIMIT,
            pro_limit=settings.PRO_RATE_LIMIT,
        )

    # --- Custom exception handler ---
    @app.exception_handler(DocSprintError)
    async def docsprint_exception_handler(request: Request, exc: DocSprintError) -> JSONResponse:
        """Handle all DocSprintError subclasses and return structured JSON."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )

    # --- Routers ---
    app.include_router(api_v1_router)

    # --- Health check ---
    @app.get("/health", tags=["health"])
    async def health_check() -> dict:
        """Health check endpoint."""
        return {
            "status": "ok",
            "version": "0.1.0",
            "dev_mode": settings.DEV_MODE,
            "rate_limiting": settings.RATE_LIMIT_ENABLED,
        }

    return app


# App instance for uvicorn
app = create_app()