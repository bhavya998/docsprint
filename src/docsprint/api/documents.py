"""Document endpoints — upload, list, get, and delete documents."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, UploadFile
from sqlalchemy.orm import Session

from docsprint.api.schemas import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from docsprint.core.dependencies import get_current_user, get_db
from docsprint.core.exceptions import (
    DocumentNotFoundError,
    QuotaExceededError,
    UnsupportedFileFormatError,
)
from docsprint.models.document import Document
from docsprint.models.user import User
from docsprint.services.document_service import (
    count_pages,
    is_supported_format,
    save_upload,
)
from docsprint.services.job_service import create_job, get_job_by_document
from docsprint.services.usage_service import check_quota, get_plan_pages_limit

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
def upload_document(
    file: UploadFile,
    mode: str = Form(default="extract"),
    prompt: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    """Upload a document for AI processing.

    Accepts PDF, PNG, JPG, GIF, TIFF, BMP, and WebP files up to 20MB.
    The document is enqueued for async processing by the GPU worker.
    Supported modes: extract (structured extraction), describe (summary),
    ask (Q&A with optional prompt).

    Args:
        file: The uploaded document file.
        mode: Processing mode (default: "extract").
        prompt: Optional question for "ask" mode.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        DocumentUploadResponse with document_id, job_id, and status.

    Raises:
        UnsupportedFileFormatError: If the file format is not supported.
        QuotaExceededError: If the user has exceeded their monthly quota.
    """
    if not is_supported_format(file.filename or ""):
        raise UnsupportedFileFormatError(file.filename or "unknown")

    # Save the file
    file_path, file_format = save_upload(file)
    page_count = count_pages(file_path, file_format)

    # Check quota before proceeding
    if not check_quota(db, current_user, additional_pages=page_count):
        limit = get_plan_pages_limit(current_user.plan)
        from docsprint.services.usage_service import get_current_usage

        used = get_current_usage(db, current_user.id)
        raise QuotaExceededError(used, limit)

    # Create document record
    document = Document(
        user_id=current_user.id,
        filename=file.filename or "unnamed",
        file_path=file_path,
        file_format=file_format,
        page_count=page_count,
        mode=mode,
        status="queued",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Deduct pages from usage quota at upload time
    from docsprint.services.usage_service import increment_usage

    increment_usage(db, current_user.id, page_count)

    # Create and enqueue job
    job = create_job(db, document, mode, prompt)

    return DocumentUploadResponse(
        document_id=document.id,
        job_id=job.id,
        status="queued",
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    """List all documents for the current user.

    Args:
        skip: Number of records to skip (pagination).
        limit: Maximum records to return (default: 20).
        current_user: Authenticated user.
        db: Database session.

    Returns:
        DocumentListResponse with documents and total count.
    """
    total = db.query(Document).filter(Document.user_id == current_user.id).count()
    documents = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in documents],
        total=total,
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentDetailResponse:
    """Get a specific document with processing results.

    Args:
        document_id: The document ID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        DocumentDetailResponse including result data if available.

    Raises:
        DocumentNotFoundError: If the document doesn't exist or belongs to another user.
    """
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not document:
        raise DocumentNotFoundError(document_id)

    # Get the job result if available
    result = None
    error = None
    job = get_job_by_document(db, document_id)
    if job:
        import json

        if job.result_json:
            try:
                result = json.loads(job.result_json)
            except (json.JSONDecodeError, TypeError):
                pass
        error = job.error

    return DocumentDetailResponse(
        id=document.id,
        filename=document.filename,
        file_format=document.file_format,
        page_count=document.page_count,
        mode=document.mode,
        status=document.status,
        created_at=document.created_at,
        completed_at=document.completed_at,
        result=result,
        error=error,
    )