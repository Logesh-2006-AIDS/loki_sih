import os
import re
from pathlib import Path
from typing import BinaryIO, List, Optional, Tuple
from app.core.exceptions import ValidationException

DEFAULT_ALLOWED_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png"]
DEFAULT_MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

# Magic byte signatures
SIGNATURES = {
    "pdf": [b"%PDF-"],
    "jpeg": [b"\xff\xd8\xff"],
    "png": [b"\x89PNG\r\n\x1a\n"],
}

MIME_MAPPING = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes an uploaded filename to prevent directory traversal,
    null-byte attacks, and shell injection.
    """
    if not filename or not isinstance(filename, str):
        raise ValidationException("Filename must be a non-empty string.")

    # Reject null bytes or path separators immediately
    if "\x00" in filename:
        raise ValidationException("Unsafe filename: null bytes detected.")

    # Check for path traversal patterns
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValidationException("Unsafe filename: directory traversal detected.")

    # Strip leading/trailing whitespace
    clean_name = os.path.basename(filename.strip())

    # Keep only safe alphanumeric characters, dashes, underscores, and dots
    clean_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", clean_name)

    if not clean_name or clean_name.startswith("."):
        raise ValidationException("Invalid or unsafe filename.")

    return clean_name


def validate_file(
    file_obj: BinaryIO,
    filename: str,
    allowed_extensions: Optional[List[str]] = None,
    max_size_bytes: int = DEFAULT_MAX_SIZE_BYTES,
) -> Tuple[str, str, int]:
    """
    Performs comprehensive security and integrity validation on an uploaded file:
    1. Path traversal and filename safety sanitization.
    2. Extension whitelist verification.
    3. Non-zero byte and maximum file size enforcement.
    4. Magic-byte signature verification to prevent spoofed extensions (e.g. .exe renamed to .pdf).

    Returns:
        Tuple of (sanitized_filename, verified_mime_type, file_size_in_bytes)
    """
    # 1. Sanitize filename
    clean_filename = sanitize_filename(filename)

    # 2. Extension validation
    ext = Path(clean_filename).suffix.lower()
    allowed = [e.lower() if e.startswith(".") else f".{e.lower()}" for e in (allowed_extensions or DEFAULT_ALLOWED_EXTENSIONS)]
    if ext not in allowed:
        raise ValidationException(
            f"File extension '{ext}' is not permitted. Allowed extensions: {', '.join(allowed)}"
        )

    # 3. Read header for magic bytes and determine size
    file_obj.seek(0, os.SEEK_END)
    file_size = file_obj.tell()
    file_obj.seek(0)

    if file_size <= 0:
        raise ValidationException("Uploaded file is empty (0 bytes).")

    if file_size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        curr_mb = file_size / (1024 * 1024)
        raise ValidationException(
            f"File size ({curr_mb:.2f} MB) exceeds the maximum allowed limit of {max_mb:.2f} MB."
        )

    # 4. Magic-byte verification
    header = file_obj.read(16)
    file_obj.seek(0)  # Rewind so file can be saved completely!

    verified_mime = MIME_MAPPING.get(ext, "application/octet-stream")

    if ext == ".pdf":
        if not any(header.startswith(sig) for sig in SIGNATURES["pdf"]):
            raise ValidationException("File content does not match a valid PDF signature.")
    elif ext in [".jpg", ".jpeg"]:
        if not any(header.startswith(sig) for sig in SIGNATURES["jpeg"]):
            raise ValidationException("File content does not match a valid JPEG image signature.")
    elif ext == ".png":
        if not any(header.startswith(sig) for sig in SIGNATURES["png"]):
            raise ValidationException("File content does not match a valid PNG image signature.")

    return clean_filename, verified_mime, file_size
