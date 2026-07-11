"""FastAPI dependencies — auth, database session, and rate limiting."""

from __future__ import annotations

from typing import Generator

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from docsprint.core.exceptions import UnauthorizedError
from docsprint.core.security import decode_access_token
from docsprint.database import SyncSessionLocal
from docsprint.models.user import User

# FastAPI HTTP Bearer security scheme
bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a database session.

    The session is automatically closed after the request completes.
    """
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> User:
    """FastAPI dependency: authenticate and return the current user.

    Supports two authentication methods (checked in order):
    1. Bearer token in Authorization header (JWT)
    2. API key in X-API-Key header

    Args:
        db: Database session.
        credentials: Optional HTTP Bearer credentials.
        x_api_key: Optional API key from X-API-Key header.

    Returns:
        The authenticated User model instance.

    Raises:
        UnauthorizedError: If neither auth method is provided or both are invalid.
    """
    user_id: int | None = None

    # Try Bearer token first
    if credentials and credentials.credentials:
        payload = decode_access_token(credentials.credentials)
        if payload and "sub" in payload:
            try:
                user_id = int(payload["sub"])
            except (ValueError, TypeError):
                pass

    # Fall back to API key
    if user_id is None and x_api_key:
        user = db.query(User).filter(User.api_key == x_api_key, User.is_active.is_(True)).first()
        if user:
            return user

    # If we got a user_id from JWT, look up the user
    if user_id is not None:
        user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
        if user:
            return user

    raise UnauthorizedError("Invalid or missing authentication credentials")


def get_optional_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> User | None:
    """FastAPI dependency: optionally authenticate the current user.

    Returns None if no valid credentials are provided. Useful for endpoints
    that work both authenticated and unauthenticated.

    Args:
        db: Database session.
        credentials: Optional HTTP Bearer credentials.
        x_api_key: Optional API key from X-API-Key header.

    Returns:
        The authenticated User or None.
    """
    try:
        return get_current_user(db=db, credentials=credentials, x_api_key=x_api_key)
    except UnauthorizedError:
        return None