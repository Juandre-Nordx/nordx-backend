"""Helpers for storing and resolving uploaded files."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse


PUBLIC_UPLOAD_PREFIX = "/uploads"
UPLOAD_VOLUME_ROOT = Path(os.getenv("UPLOAD_DIR", "/data")).expanduser()
UPLOAD_ROOT = Path(
    os.getenv(
        "UPLOAD_STORAGE_DIR",
        str(
            UPLOAD_VOLUME_ROOT
            if UPLOAD_VOLUME_ROOT.name == "uploads"
            else UPLOAD_VOLUME_ROOT / "uploads"
        ),
    )
).expanduser()
LEGACY_DATA_ROOT = UPLOAD_VOLUME_ROOT
LEGACY_UPLOAD_ROOT = Path("/data/uploads")


def ensure_upload_root() -> Path:
    """Create and return the directory that stores upload subfolders."""
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    return UPLOAD_ROOT


def ensure_upload_subdir(subfolder: str) -> Path:
    """Create and return a subdirectory inside the upload root."""
    folder = ensure_upload_root() / subfolder
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def public_upload_path(subfolder: str, filename: str) -> str:
    """Return the URL path stored in the database for an uploaded file."""
    return f"{PUBLIC_UPLOAD_PREFIX}/{subfolder.strip('/')}/{filename}"


def upload_relative_path(db_path: str) -> Path:
    """Convert a public upload URL like /uploads/before/a.jpg to before/a.jpg."""
    path_text = str(db_path or "")
    parsed = urlparse(path_text)
    normalized = unquote(parsed.path or path_text).replace("\\", "/").lstrip("/")

    if normalized.startswith("uploads/"):
        normalized = normalized[len("uploads/"):]

    relative = PurePosixPath(normalized)
    unsafe_path = (
        not normalized
        or relative.is_absolute()
        or any(part in ("", ".", "..") for part in relative.parts)
    )
    if unsafe_path:
        raise ValueError("Invalid upload path")

    return Path(*relative.parts)


def resolve_upload_path(db_path: str) -> Path:
    """
    Resolve a database-stored upload URL to its configured disk location.

    The database stores public URLs under /uploads/... while the app stores
    files in an uploads folder inside the mounted UPLOAD_DIR volume. For
    example, UPLOAD_DIR=/data maps /uploads/before/a.jpg to
    /data/uploads/before/a.jpg. Older direct-to-volume layouts such as
    /data/before/a.jpg are still checked as fallbacks.
    """
    path_text = str(db_path)
    absolute = Path(path_text)
    is_private_absolute_path = (
        absolute.is_absolute()
        and absolute.exists()
        and not path_text.startswith(PUBLIC_UPLOAD_PREFIX)
    )
    if is_private_absolute_path:
        return absolute

    relative = upload_relative_path(path_text)
    configured_path = ensure_upload_root() / relative
    if configured_path.exists():
        return configured_path

    fallback_roots = [LEGACY_DATA_ROOT, LEGACY_UPLOAD_ROOT]
    for root in fallback_roots:
        fallback_path = root / relative
        if fallback_path != configured_path and fallback_path.exists():
            return fallback_path

    return configured_path
