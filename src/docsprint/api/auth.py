"""Auth endpoints — registration, login, and user profile."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from docsprint.api.schemas import (
    AuthResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from docsprint.core.dependencies import get_current_user, get_db
from docsprint.core.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
)
from docsprint.core.security import create_access_token, hash_password, verify_password
from docsprint.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(
    body: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    """Register a new user account.

    Creates a new user with a bcrypt-hashed password and returns a JWT
    access token along with the user profile. The user also receives
    a unique API key (dsk_ prefix) for programmatic access.

    Args:
        body: Registration details (email + password).
        db: Database session.

    Returns:
        AuthResponse with access_token and user profile.

    Raises:
        UserAlreadyExistsError: If the email is already registered.
    """
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise UserAlreadyExistsError(body.email)

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(data={"sub": str(user.id)})
    return AuthResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=AuthResponse)
def login(
    body: UserLoginRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    """Authenticate a user and return a JWT access token.

    Args:
        body: Login credentials (email + password).
        db: Database session.

    Returns:
        AuthResponse with access_token and user profile.

    Raises:
        InvalidCredentialsError: If email or password is incorrect.
    """
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise InvalidCredentialsError()

    if not user.is_active:
        raise InvalidCredentialsError("Account is deactivated")

    access_token = create_access_token(data={"sub": str(user.id)})
    return AuthResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the current authenticated user's profile.

    Requires a valid Bearer token or X-API-Key header.

    Args:
        current_user: Authenticated user (injected by dependency).

    Returns:
        UserResponse with full profile including API key.
    """
    return UserResponse.model_validate(current_user)