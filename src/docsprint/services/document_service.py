"""Document service — file upload handling, validation, and storage."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import fitz  # pymupdf
from fastapi import UploadFile
from PIL import Image

from docsprint.config import settings

# Supported file extensions
_SUPPORTED_FORMATS: dict[str, str] = {
    ".pdf": "pdf",
    ".png": "png",
    ".jpg": "jpg",
    ".jpeg": "jpg",
    ".gif": "gif",
    ".tiff": "tiff",
    ".tif": "tiff",
    ".bmp": "bmp",
    ".webp": "webp",
}


def is_supported_format(filename: str) -> bool:
    """Check if the file extension is supported.

    Args:
        filename: Original filename with extension.

    Returns:
        True if the format is supported.
    """
    suffix = Path(filename).suffix.lower()
    return suffix in _SUPPORTED_FORMATS


def get_file_format(filename: str) -> str:
    """Get the normalized file format from a filename.

    Args:
        filename: Original filename with extension.

    Returns:
        Normalized format string (e.g. "pdf", "png", "jpg").

    Raises:
        ValueError: If the format is not supported.
    """
    suffix = Path(filename).suffix.lower()
    fmt = _SUPPORTED_FORMATS.get(suffix)
    if fmt is None:
        raise ValueError(f"Unsupported format: {suffix}")
    return fmt


def validate_file_size(file: UploadFile) -> None:
    """Validate that the uploaded file is within size limits.

    Args:
        file: The uploaded file object.

    Raises:
        ValueError: If the file exceeds the max size.
    """
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    file.file.seek(0, 2)  # Seek to end
    size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    if size > max_bytes:
        raise ValueError(f"File exceeds maximum size of {settings.MAX_FILE_SIZE_MB}MB")


def save_upload(file: UploadFile) -> tuple[str, str]:
    """Save an uploaded file to disk and return its path and format.

    Args:
        file: The uploaded file object.

    Returns:
        Tuple of (file_path, file_format).

    Raises:
        ValueError: If the file format is not supported or size exceeds limit.
    """
    validate_file_size(file)

    original_name = file.filename or "unnamed"
    fmt = get_file_format(original_name)
    ext = Path(original_name).suffix.lower()

    # Generate unique filename
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = settings.upload_path / unique_name

    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return str(dest_path.resolve()), fmt


def count_pages(file_path: str, file_format: str) -> int:
    """Count the number of pages/frames in a document.

    Args:
        file_path: Path to the saved file.
        file_format: Normalized format string.

    Returns:
        Number of pages (PDF) or frames (GIF), 1 for images.
    """
    if file_format == "pdf":
        try:
            doc = fitz.open(file_path)
            count = len(doc)
            doc.close()
            return count
        except Exception:
            return 0
    elif file_format == "gif":
        try:
            with Image.open(file_path) as img:
                return getattr(img, "n_frames", 1)
        except Exception:
            return 1
    else:
        return 1  # Single-page image


def delete_file(file_path: str) -> None:
    """Delete a file from disk if it exists.

    Args:
        file_path: Path to the file to delete.
    """
    path = Path(file_path)
    if path.exists():
        path.unlink()