"""Main API router — includes all sub-routers under /api/v1 prefix."""

from __future__ import annotations

from fastapi import APIRouter

from docsprint.api import auth, documents, jobs, usage

# Main v1 router
api_v1_router = APIRouter(prefix="/api/v1")

# Include all sub-routers
api_v1_router.include_router(auth.router)
api_v1_router.include_router(documents.router)
api_v1_router.include_router(jobs.router)
api_v1_router.include_router(jobs.documents_result_router)
api_v1_router.include_router(usage.router)