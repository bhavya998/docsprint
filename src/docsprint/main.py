"""FastAPI application factory — CORS, routers, and exception handlers."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from docsprint.api.router import api_v1_router
from docsprint.config import settings
from docsprint.core.exceptions import DocSprintError


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

    Sets up CORS, includes the v1 API router, and registers custom
    exception handlers for DocSprintError subclasses.

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
        return {"status": "ok", "version": "0.1.0"}

    return app


# App instance for uvicorn
app = create_app()