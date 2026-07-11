"""Pydantic v2 schemas — request/response models for all API endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ──────────────────────────────────────────────
# Auth schemas
# ──────────────────────────────────────────────


class UserRegisterRequest(BaseModel):
    """Request body for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserLoginRequest(BaseModel):
    """Request body for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public user profile returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    plan: str
    api_key: str
    is_active: bool
    created_at: datetime


class AuthResponse(BaseModel):
    """Combined auth response: token + user."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ──────────────────────────────────────────────
# Document schemas
# ──────────────────────────────────────────────


class DocumentUploadResponse(BaseModel):
    """Response after a document is uploaded and queued for processing."""

    document_id: int
    job_id: int
    status: str
    message: str = "Document queued for processing"


class DocumentResponse(BaseModel):
    """Document metadata returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_format: str
    page_count: int
    mode: str
    status: str
    created_at: datetime
    completed_at: datetime | None = None


class DocumentDetailResponse(DocumentResponse):
    """Document detail including processing result."""

    result: dict | None = None
    error: str | None = None


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    documents: list[DocumentResponse]
    total: int


# ──────────────────────────────────────────────
# Job schemas
# ──────────────────────────────────────────────


class JobResponse(BaseModel):
    """Job status and result."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    status: str
    result_json: dict | None = None
    error: str | None = None
    processing_time_seconds: float | None = None
    created_at: datetime
    completed_at: datetime | None = None


class JobListResponse(BaseModel):
    """List of jobs."""

    jobs: list[JobResponse]
    total: int


# ──────────────────────────────────────────────
# Result schemas
# ──────────────────────────────────────────────


class PageResult(BaseModel):
    """Result for a single page of a document."""

    page: int
    content: str
    has_extracted_text: bool = False


class DocumentResultResponse(BaseModel):
    """Structured document processing result."""

    pages: list[PageResult]
    format: str


# ──────────────────────────────────────────────
# Usage schemas
# ──────────────────────────────────────────────


class UsageResponse(BaseModel):
    """Current usage and plan limits."""

    plan: str
    pages_used: int
    pages_limit: int
    period: str  # e.g. "2026-07"


class UsageHistoryItem(BaseModel):
    """A single monthly usage record."""

    month: int
    year: int
    pages_processed: int


class UsageHistoryResponse(BaseModel):
    """Full usage history."""

    records: list[UsageHistoryItem]
    total: int