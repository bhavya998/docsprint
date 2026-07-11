"""Job model — processing tasks queued for the GPU worker."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from docsprint.database import Base


class Job(Base):
    """A processing job associated with a document.

    Each document has exactly one job. The RQ worker picks up queued jobs,
    runs the VL model, and updates status + result_json on completion.
    """

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="queued", nullable=False
    )  # queued, processing, completed, failed
    result_json: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None
    )  # JSON string from model output
    error: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    processing_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="jobs")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<Job(id={self.id}, document_id={self.document_id}, "
            f"status='{self.status}')>"
        )