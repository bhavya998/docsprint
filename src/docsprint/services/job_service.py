"""Job service — create jobs, enqueue to Redis, check status."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from redis import Redis
from rq import Queue
from sqlalchemy.orm import Session

from docsprint.config import settings
from docsprint.models.document import Document
from docsprint.models.job import Job


def get_redis_connection() -> Redis:
    """Create a Redis connection from settings.

    Returns:
        Redis client instance.
    """
    return Redis.from_url(settings.REDIS_URL)


def get_queue(connection: Redis | None = None) -> Queue:
    """Get the RQ queue for document processing.

    Args:
        connection: Optional Redis connection. Creates one if not provided.

    Returns:
        RQ Queue named "doc-processing".
    """
    redis_conn = connection or get_redis_connection()
    return Queue("doc-processing", connection=redis_conn)


def create_job(
    db: Session,
    document: Document,
    mode: str,
    prompt: str | None = None,
) -> Job:
    """Create a new processing job and enqueue it to Redis.

    Args:
        db: Database session.
        document: The Document model instance to process.
        mode: Processing mode ("extract", "describe", "ask").
        prompt: Optional custom prompt for "ask" mode.

    Returns:
        The created Job model instance.

    Raises:
        ValueError: If mode is invalid.
    """
    if mode not in ("extract", "describe", "ask"):
        raise ValueError(f"Invalid mode: {mode}. Must be one of: extract, describe, ask")

    job = Job(
        document_id=document.id,
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Enqueue the job for async processing
    try:
        queue = get_queue()
        queue.enqueue(
            "docsprint.workers.inference_worker.process_document_job",
            job_id=job.id,
            document_id=document.id,
            file_path=document.file_path,
            file_format=document.file_format,
            mode=mode,
            prompt=prompt or "",
        )
    except Exception as exc:
        # Redis unavailable — job stays queued, worker can pick it up later
        print(f"[DocSprint] Warning: Could not enqueue job {job.id}: {exc}")

    return job


def get_job(db: Session, job_id: int) -> Job | None:
    """Fetch a job by ID.

    Args:
        db: Database session.
        job_id: The job ID.

    Returns:
        Job instance or None if not found.
    """
    return db.query(Job).filter(Job.id == job_id).first()


def get_job_by_document(db: Session, document_id: int) -> Job | None:
    """Fetch the job associated with a document.

    Args:
        db: Database session.
        document_id: The document ID.

    Returns:
        Job instance or None if not found.
    """
    return db.query(Job).filter(Job.document_id == document_id).first()


def update_job_status(
    db: Session,
    job: Job,
    status: str,
    result_json: dict | None = None,
    error: str | None = None,
    processing_time_seconds: float | None = None,
) -> Job:
    """Update a job's status and optionally its result/error/time.

    Args:
        db: Database session.
        job: The Job to update.
        status: New status ("queued", "processing", "completed", "failed").
        result_json: Optional result data from the model.
        error: Optional error message.
        processing_time_seconds: Optional processing duration.

    Returns:
        The updated Job instance.
    """
    job.status = status

    if result_json is not None:
        job.result_json = json.dumps(result_json)

    if error is not None:
        job.error = error

    if processing_time_seconds is not None:
        job.processing_time_seconds = processing_time_seconds

    if status in ("completed", "failed"):
        job.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(job)

    # Also update the document status
    document = db.query(Document).filter(Document.id == job.document_id).first()
    if document:
        document.status = status
        if status == "completed":
            document.completed_at = datetime.now(timezone.utc)
        db.commit()

    return job


def get_user_jobs(db: Session, user_id: int, skip: int = 0, limit: int = 20) -> tuple[list[Job], int]:
    """Get all jobs for a user's documents.

    Args:
        db: Database session.
        user_id: The user's ID.
        skip: Number of records to skip (pagination).
        limit: Maximum records to return.

    Returns:
        Tuple of (list of Job instances, total count).
    """
    doc_ids = (
        db.query(Document.id)
        .filter(Document.user_id == user_id)
        .subquery()
    )
    total = db.query(Job).filter(Job.document_id.in_(doc_ids)).count()
    jobs = (
        db.query(Job)
        .filter(Job.document_id.in_(doc_ids))
        .order_by(Job.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return jobs, total