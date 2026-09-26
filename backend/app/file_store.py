"""Keeps the original PDF files so users can open, download and summarise them."""

import re
from pathlib import Path

from app.config import get_settings

# Document ids are the first 16 hex characters of a SHA-256 hash. Accepting
# nothing else means a request like "../../.env" can never reach the disk.
_DOCUMENT_ID = re.compile(r"[0-9a-f]{16}")


def save(document_id: str, data: bytes) -> None:
    path = _path(document_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def delete(document_id: str) -> None:
    path = path_for(document_id)
    if path is not None:
        path.unlink()


def path_for(document_id: str) -> Path | None:
    """The stored file, or None if the id is invalid or nothing is stored."""
    if not _DOCUMENT_ID.fullmatch(document_id):
        return None
    path = _path(document_id)
    return path if path.is_file() else None


def _path(document_id: str) -> Path:
    return Path(get_settings().documents_dir) / f"{document_id}.pdf"
