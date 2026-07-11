"""Custom exceptions and HTTP exception handlers for DocSprint."""

from __future__ import annotations

from fastapi import status


class DocSprintError(Exception):
    """Base exception for all DocSprint-specific errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class InvalidCredentialsError(DocSprintError):
    """Raised when login credentials are invalid."""

    def __init__(self, message: str = "Invalid email or password") -> None:
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)


class UserAlreadyExistsError(DocSprintError):
    """Raised when trying to register an email that already exists."""

    def __init__(self, email: str) -> None:
        super().__init__(
            f"User with email '{email}' already exists",
            status_code=status.HTTP_409_CONFLICT,
        )


class UserNotFoundError(DocSprintError):
    """Raised when a user cannot be found."""

    def __init__(self, user_id: int | None = None, email: str | None = None) -> None:
        detail = f"User not found: {user_id or email}"
        super().__init__(detail, status_code=status.HTTP_404_NOT_FOUND)


class DocumentNotFoundError(DocSprintError):
    """Raised when a document cannot be found."""

    def __init__(self, document_id: int) -> None:
        super().__init__(
            f"Document not found: {document_id}",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class JobNotFoundError(DocSprintError):
    """Raised when a job cannot be found."""

    def __init__(self, job_id: int) -> None:
        super().__init__(
            f"Job not found: {job_id}",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class QuotaExceededError(DocSprintError):
    """Raised when a user has exceeded their monthly page quota."""

    def __init__(self, pages_used: int, pages_limit: int) -> None:
        super().__init__(
            f"Monthly quota exceeded: {pages_used}/{pages_limit} pages used",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


class FileTooLargeError(DocSprintError):
    """Raised when an uploaded file exceeds the maximum allowed size."""

    def __init__(self, max_size_mb: int) -> None:
        super().__init__(
            f"File too large. Maximum size is {max_size_mb}MB",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )


class UnsupportedFileFormatError(DocSprintError):
    """Raised when an uploaded file has an unsupported format."""

    def __init__(self, file_format: str) -> None:
        super().__init__(
            f"Unsupported file format: {file_format}. "
            "Supported formats: PDF, PNG, JPG, GIF, TIFF, BMP, WebP",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class UnauthorizedError(DocSprintError):
    """Raised when authentication is required but missing or invalid."""

    def __init__(self, message: str = "Not authenticated") -> None:
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)