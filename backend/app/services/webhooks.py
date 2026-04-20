"""Outbound webhook delivery — typically consumed by Power Automate flows.

Each delivery is persisted in ``webhook_deliveries`` for retry / audit. We
sign the payload with HMAC-SHA256 using ``WEBHOOK_SIGNING_SECRET`` so the
receiver can verify authenticity before triggering any downstream automation.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential

from .. import models
from ..config import settings
from . import cosmos_events
from .observability import get_logger

log = get_logger(__name__)

_TARGETS = {
    "draft.created": lambda: settings.webhook_url_draft_created,
    "draft.approved": lambda: settings.webhook_url_draft_approved,
}


def _sign(body: bytes) -> str:
    if not settings.webhook_signing_secret:
        return ""
    return hmac.new(
        settings.webhook_signing_secret.encode("utf-8"),
        body, hashlib.sha256,
    ).hexdigest()


def enqueue_webhook(db: Session, org_id: int, event: str, payload: dict[str, Any]) -> None:
    # Mirror every event into Cosmos (no-op when not configured) so we have an
    # immutable audit record independent of webhook delivery success.
    cosmos_events.emit(event, org_id=org_id, payload=payload)
    target = _TARGETS.get(event, lambda: "")()
    if not target:
        return  # event not configured — silently skip
    body = json.dumps(payload, default=str).encode("utf-8")
    delivery = models.WebhookDelivery(
        org_id=org_id, event=event, target_url=target,
        payload=body.decode("utf-8"),
    )
    db.add(delivery)
    db.commit()
    db.refresh(delivery)
    try:
        _deliver(delivery.id, target, body)
        delivery.delivered = True
        delivery.status_code = 200
    except Exception as e:
        delivery.error = str(e)[:500]
        log.warning("webhook_delivery_failed", event=event, error=str(e))
    finally:
        delivery.attempts = (delivery.attempts or 0) + 1
        delivery.last_attempt_at = datetime.utcnow()
        db.commit()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
def _deliver(delivery_id: int, url: str, body: bytes) -> None:
    headers = {
        "Content-Type": "application/json",
        "X-SJ-Event-Delivery-Id": str(delivery_id),
    }
    sig = _sign(body)
    if sig:
        headers["X-SJ-Signature"] = f"sha256={sig}"
    with httpx.Client(timeout=10.0) as cli:
        r = cli.post(url, content=body, headers=headers)
        r.raise_for_status()
