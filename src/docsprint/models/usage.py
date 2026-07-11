"""Usage record model — monthly page-processing tracking per user."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from docsprint.database import Base


class UsageRecord(Base):
    """Monthly usage tracking for billing and quota enforcement.

    Each row represents one user's total pages processed in a given month.
    Unique constraint on (user_id, month, year) ensures one record per period.
    """

    __tablename__ = "usage_records"
    __table_args__ = (
        UniqueConstraint("user_id", "month", "year", name="uq_user_month_year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pages_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<UsageRecord(id={self.id}, user_id={self.user_id}, "
            f"period={self.year}-{self.month:02d}, pages={self.pages_processed})>"
        )