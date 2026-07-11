"""User model — authentication, plan tier, and API key."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from docsprint.database import Base


def _generate_api_key() -> str:
    """Generate a unique API key with dsk_ prefix."""
    return f"dsk_{secrets.token_hex(24)}"


class User(Base):
    """A registered user of the DocSprint platform."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(
        String(20), default="free", nullable=False
    )  # free, starter, pro
    api_key: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, default=_generate_api_key
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', plan='{self.plan}')>"