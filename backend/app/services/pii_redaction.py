"""Lightweight PII scrubber applied before sending free-text to the LLM.

Patterns are conservative — we replace clearly identifiable strings with
placeholders (``[EMAIL]``, ``[PHONE]``, ``[ID]``) but leave names alone since
the agent legitimately needs them to assign owners. Disable with
``REDACT_PII=false`` in ``.env`` if you trust the channel end-to-end.
"""
from __future__ import annotations

import re

from ..config import settings

_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(\d{2,4}\)|\d{2,4})[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b")
_NRIC = re.compile(r"\b[STFGM]\d{7}[A-Z]\b")  # Singapore NRIC/FIN
_CREDIT = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
_API_KEY = re.compile(r"\b(?:sk|pk|api|key|token)[_-][A-Za-z0-9]{16,}\b", re.IGNORECASE)


def redact(text: str) -> str:
    if not text or not settings.redact_pii:
        return text or ""
    out = _EMAIL.sub("[EMAIL]", text)
    out = _PHONE.sub("[PHONE]", out)
    out = _NRIC.sub("[ID]", out)
    out = _CREDIT.sub("[CARD]", out)
    out = _API_KEY.sub("[SECRET]", out)
    return out
