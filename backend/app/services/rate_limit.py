"""SlowAPI rate-limiter shared across the application.

Keying strategy: prefer the authenticated user id (from JWT ``sub`` claim) so
multiple users behind a NAT are not unfairly throttled; fall back to client IP
for unauthenticated requests.
"""
from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        # Token's `sub` is sufficient for keying; we don't need to verify here —
        # SlowAPI keys are not security boundaries, just bucketing.
        token = auth.split(None, 1)[1]
        try:
            import base64, json
            payload = token.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            sub = json.loads(base64.urlsafe_b64decode(payload)).get("sub")
            if sub:
                return f"user:{sub}"
        except Exception:
            pass
    return get_remote_address(request)


limiter = Limiter(key_func=_key, default_limits=["120/minute"])
