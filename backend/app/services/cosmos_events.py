"""Optional Cosmos DB event mirror.

When ``COSMOS_CONNECTION_STRING`` (and database/container) is configured every
audit-worthy event (change-log writes, webhook attempts, draft decisions) is
mirrored as a JSON document. Useful for long-term retention and downstream
analytics in Power BI / Synapse without straining the relational store.

When unconfigured this module is a no-op so the rest of the app can call
:func:`emit` unconditionally.
"""
from __future__ import annotations

import os
import threading
import uuid
from datetime import datetime
from typing import Any

from ..config import settings
from .observability import get_logger

log = get_logger(__name__)

_lock = threading.Lock()
_container = None
_init_attempted = False


def _client():
    """Lazily build (and cache) a Cosmos container client."""
    global _container, _init_attempted
    if _container is not None or _init_attempted:
        return _container
    with _lock:
        if _container is not None or _init_attempted:
            return _container
        _init_attempted = True
        if not settings.cosmos_enabled or os.getenv("COSMOS_DISABLE", "0") == "1":
            return None
        try:
            from azure.cosmos import CosmosClient, PartitionKey
        except ImportError:
            log.info("cosmos_sdk_missing")
            return None
        try:
            cli = CosmosClient.from_connection_string(settings.cosmos_connection_string)
            db = cli.create_database_if_not_exists(settings.cosmos_database)
            _container = db.create_container_if_not_exists(
                id=settings.cosmos_container,
                partition_key=PartitionKey(path="/org_id"),
            )
            log.info("cosmos_ready", database=settings.cosmos_database,
                     container=settings.cosmos_container)
        except Exception as e:  # noqa: BLE001
            log.warning("cosmos_init_failed", error=str(e))
            _container = None
        return _container


def emit(event_type: str, *, org_id: int, payload: dict[str, Any]) -> None:
    """Best-effort mirror of an event into Cosmos. Never raises."""
    container = _client()
    if container is None:
        return
    try:
        doc = {
            "id": str(uuid.uuid4()),
            "org_id": str(org_id),
            "event_type": event_type,
            "ts": datetime.utcnow().isoformat() + "Z",
            "payload": payload,
        }
        container.create_item(doc)
    except Exception as e:  # noqa: BLE001
        log.warning("cosmos_emit_failed", event=event_type, error=str(e))
