"""RQ worker function — processes queued document jobs.

This module is imported by the RQ worker process. It receives job data,
runs the VL model on the document, and updates the job status in the database.
Usage is tracked at upload time (not here) to avoid double-counting.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from docsprint.config import settings
from docsprint.database import SyncSessionLocal
from docsprint.models.document import Document
from docsprint.models.job import Job
from docsprint.services.model_service import VLModelService

# Global model instance — loaded once per worker process
_model_service: VLModelService | None = None


def _get_model() -> VLModelService:
    """Get or create the global VL model service instance.

    The model is loaded lazily on first job so the worker can start
    without immediately consuming GPU memory.

    Returns:
        Singleton VLModelService instance.
    """
    global _model_service
    if _model_service is None:
        _model_service = VLModelService(
            model_id=settings.MODEL_ID,
            quantize_4bit=settings.MODEL_QUANTIZE_4BIT,
        )
    return _model_service


def process_document_job(
    job_id: int,
    document_id: int,
    file_path: str,
    file_format: str,
    mode: str,
    prompt: str = "",
) -> dict:
    """Process a document through the VL model and update job status.

    This is the entry point called by RQ when a job is dequeued.

    Args:
        job_id: The Job ID in the database.
        document_id: The Document ID.
        file_path: Path to the saved document file.
        file_format: Normalized file format.
        mode: Processing mode ("extract", "describe", "ask").
        prompt: Optional custom prompt for extract/ask modes.

    Returns:
        The result dict from the model.
    """
    db = SyncSessionLocal()
    start_time = time.time()

    try:
        # Update status to processing
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "processing"
            db.commit()

        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = "processing"
            db.commit()

        # Run the model
        model = _get_model()
        result = model.process_document(file_path, mode, prompt)
        elapsed = time.time() - start_time

        # Update job with results
        import json

        if job:
            job.status = "completed"
            job.result_json = json.dumps(result)
            job.processing_time_seconds = round(elapsed, 2)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()

        if document:
            document.status = "completed"
            document.completed_at = datetime.now(timezone.utc)
            db.commit()

        print(f"[DocSprint Worker] Job {job_id} completed in {elapsed:.2f}s")
        return result

    except Exception as exc:
        elapsed = time.time() - start_time
        error_msg = f"{type(exc).__name__}: {exc}"

        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "failed"
            job.error = error_msg
            job.processing_time_seconds = round(elapsed, 2)
            db.commit()

        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = "failed"
            db.commit()

        print(f"[DocSprint Worker] Job {job_id} FAILED: {error_msg}")
        raise

    finally:
        db.close()