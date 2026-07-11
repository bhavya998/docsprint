"""SQLAlchemy engine and session factory.

Uses SQLAlchemy 2.0 style with sync engine.
The engine is created lazily so tests can override the DATABASE_URL.
"""

from __future__ import annotations

from typing import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from docsprint.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


_engine: Engine | None = None
_SyncSessionLocal: sessionmaker[Session] | None = None


def _get_engine() -> Engine:
    """Get or create the SQLAlchemy sync engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False,
        )
    return _engine


def _get_session_factory() -> sessionmaker[Session]:
    """Get or create the session factory."""
    global _SyncSessionLocal
    if _SyncSessionLocal is None:
        _SyncSessionLocal = sessionmaker(
            bind=_get_engine(),
            autocommit=False,
            autoflush=False,
        )
    return _SyncSessionLocal


def SyncSessionLocal() -> Session:
    """Create a new sync database session.

    This is a function (not a sessionmaker property) so it can be
    monkeypatched in tests. Returns a fresh Session each call.
    """
    return _get_session_factory()()


def get_sync_db() -> Generator[Session, None, None]:
    """Yield a synchronous database session.

    Used by CLI commands, RQ workers, and Alembic migrations.
    """
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()