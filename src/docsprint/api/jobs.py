"""Job endpoints — job status, results, and listing."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from docsprint.api.schemas import (
    DocumentResultResponse,
    JobListResponse,
    JobResponse,
    PageResult,
)
from docsprint.core.dependencies import get_current_user, get_db
from docsprint.core.exceptions import DocumentNotFoundError, JobNotFoundError
from docsprint.models.document import Document
from docsprint.models.user import User
from docsprint.services.job_service import get_job, get_job_by_document, get_user_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=JobListResponse)
def list_jobs(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobListResponse:
    """List all jobs for the current user's documents.

    Args:
        skip: Number of records to skip (pagination).
        limit: Maximum records to return (default: 20).
        current_user: Authenticated user.
        db: Database session.

    Returns:
        JobListResponse with jobs and total count.
    """
    jobs, total = get_user_jobs(db, current_user.id, skip, limit)

    job_responses: list[JobResponse] = []
    for job in jobs:
        result = None
        if job.result_json:
            try:
                result = json.loads(job.result_json)
            except (json.JSONDecodeError, TypeError):
                pass
        job_responses.append(
            JobResponse(
                id=job.id,
                document_id=job.document_id,
                status=job.status,
                result_json=result,
                error=job.error,
                processing_time_seconds=job.processing_time_seconds,
                created_at=job.created_at,
                completed_at=job.completed_at,
            )
        )

    return JobListResponse(jobs=job_responses, total=total)


@router.get("/{job_id}", response_model=JobResponse)
def get_job_status(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    """Get the status and result of a specific job.

    Args:
        job_id: The job ID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        JobResponse with status, result, and timing info.

    Raises:
        JobNotFoundError: If the job doesn't exist or belongs to another user.
    """
    job = get_job(db, job_id)
    if not job:
        raise JobNotFoundError(job_id)

    # Verify ownership through the document
    document = db.query(Document).filter(Document.id == job.document_id).first()
    if not document or document.user_id != current_user.id:
        raise JobNotFoundError(job_id)

    result = None
    if job.result_json:
        try:
            result = json.loads(job.result_json)
        except (json.JSONDecodeError, TypeError):
            pass

    return JobResponse(
        id=job.id,
        document_id=job.document_id,
        status=job.status,
        result_json=result,
        error=job.error,
        processing_time_seconds=job.processing_time_seconds,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


# Result endpoint under /documents/{id}/result per spec
documents_result_router = APIRouter(tags=["results"])


@documents_result_router.get("/documents/{document_id}/result", response_model=DocumentResultResponse)
def get_document_result(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentResultResponse:
    """Get the structured processing result for a document.

    Args:
        document_id: The document ID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        DocumentResultResponse with page-level results.

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

    job = get_job_by_document(db, document_id)
    pages: list[PageResult] = []

    if job and job.result_json:
        try:
            result_data = json.loads(job.result_json)
            # Handle different result shapes based on mode
            if isinstance(result_data, dict):
                if "pages" in result_data:
                    # Extract mode: { "pages": [...] }
                    for p in result_data["pages"]:
                        pages.append(
                            PageResult(
                                page=p.get("page", 1),
                                content=p.get("content", json.dumps(p)),
                                has_extracted_text=p.get("has_extracted_text", False),
                            )
                        )
                elif "description" in result_data:
                    # Describe mode: { "description": "..." }
                    pages.append(
                        PageResult(
                            page=1,
                            content=result_data["description"],
                            has_extracted_text=True,
                        )
                    )
                elif "answer" in result_data:
                    # Ask mode: { "answer": "..." }
                    pages.append(
                        PageResult(
                            page=1,
                            content=result_data["answer"],
                            has_extracted_text=True,
                        )
                    )
                else:
                    pages.append(
                        PageResult(page=1, content=json.dumps(result_data), has_extracted_text=True)
                    )
            elif isinstance(result_data, list):
                for i, item in enumerate(result_data):
                    pages.append(
                        PageResult(
                            page=i + 1,
                            content=item.get("content", json.dumps(item)) if isinstance(item, dict) else str(item),
                            has_extracted_text=item.get("has_extracted_text", False) if isinstance(item, dict) else False,
                        )
                    )
        except (json.JSONDecodeError, TypeError):
            pass

    return DocumentResultResponse(pages=pages, format=document.file_format)