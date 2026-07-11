"""Document model — uploaded files with processing status."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from docsprint.database import Base


class Document(Base):
    """An uploaded document submitted for AI processing."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_format: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # pdf, png, jpg, gif, tiff, bmp, webp
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mode: Mapped[str] = mapped_column(
        String(20), default="extract", nullable=False
    )  # extract, describe, ask
    status: Mapped[str] = mapped_column(
        String(20), default="queued", nullable=False
    )  # queued, processing, completed, failed
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", lazy="selectin")  # noqa: F821
    jobs: Mapped[list["Job"]] = relationship(  # noqa: F821
        "Job", back_populates="document", lazy="selectin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Document(id={self.id}, filename='{self.filename}', "
            f"status='{self.status}', format='{self.file_format}')>"
        )