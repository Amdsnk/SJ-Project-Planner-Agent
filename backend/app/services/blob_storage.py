"""Pluggable binary storage for note attachments.

Backend selection (in priority order):

1. **Azure Blob Storage** when ``AZURE_STORAGE_CONNECTION_STRING`` (or the
   account+key pair) and ``AZURE_STORAGE_CONTAINER`` are configured.
2. **Local filesystem** otherwise — files land under
   ``backend/data/attachments/`` so the demo runs offline.

The interface returns a ``StoredBlob`` describing where the bytes live so the
caller can persist a ``NoteAttachment`` row.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterator

from ..config import settings

def _local_root() -> Path:
    """Resolve the local-fs attachment directory each call so tests can swap it."""
    override = os.getenv("LOCAL_ATTACHMENT_ROOT")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "data" / "attachments"


@dataclass
class StoredBlob:
    key: str
    backend: str  # "azure" | "local"
    size_bytes: int


def _azure_enabled() -> bool:
    return bool(
        getattr(settings, "azure_storage_connection_string", "")
        and getattr(settings, "azure_storage_container", "")
    )


def _azure_client():
    """Return a ContainerClient or None if the SDK / config is unavailable."""
    if not _azure_enabled():
        return None
    try:
        from azure.storage.blob import BlobServiceClient
    except ImportError:
        return None
    svc = BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)
    container = svc.get_container_client(settings.azure_storage_container)
    try:
        container.create_container()
    except Exception:  # already exists / forbidden — fine, treat as ready
        pass
    return container


def _make_key(project_id: int, note_id: int, filename: str) -> str:
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
    return f"projects/{project_id}/notes/{note_id}/{uuid.uuid4().hex}_{safe}"


def upload(project_id: int, note_id: int, filename: str,
           data: bytes | BinaryIO) -> StoredBlob:
    key = _make_key(project_id, note_id, filename)
    payload = data.read() if hasattr(data, "read") else data

    container = _azure_client()
    if container is not None:
        container.upload_blob(name=key, data=payload, overwrite=True)
        return StoredBlob(key=key, backend="azure", size_bytes=len(payload))

    target = _local_root() / key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return StoredBlob(key=key, backend="local", size_bytes=len(payload))


def stream(key: str, backend: str) -> Iterator[bytes]:
    if backend == "azure":
        container = _azure_client()
        if container is None:
            raise RuntimeError("Azure Blob Storage is not configured")
        downloader = container.download_blob(key)
        for chunk in downloader.chunks():
            yield chunk
        return

    path = _local_root() / key
    if not path.exists():
        raise FileNotFoundError(key)
    with path.open("rb") as f:
        while True:
            chunk = f.read(64 * 1024)
            if not chunk:
                break
            yield chunk


def delete(key: str, backend: str) -> None:
    if backend == "azure":
        container = _azure_client()
        if container is None:
            return
        try:
            container.delete_blob(key)
        except Exception:
            pass
        return

    path = _local_root() / key
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def backend_active() -> str:
    return "azure" if _azure_enabled() and _azure_client() is not None else "local"


# Honour an opt-out for tests / completely offline scenarios.
if os.getenv("BLOB_FORCE_LOCAL", "0") == "1":
    def _azure_client():  # type: ignore[no-redef]
        return None
