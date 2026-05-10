"""Azure OpenAI / Microsoft Foundry client wrapper.

Returns ``None`` when LLM credentials are not configured, allowing callers to
fall back to deterministic logic. This keeps the demo end-to-end runnable
offline while remaining production-ready for Microsoft Agent Framework.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from ..config import settings
from .pii_redaction import redact

log = logging.getLogger(__name__)

_client = None


def get_client():
    global _client
    if _client is not None or not settings.llm_enabled:
        return _client
    try:
        from openai import AzureOpenAI
        _client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint,
        )
    except Exception as e:  # pragma: no cover
        log.warning("Azure OpenAI client unavailable: %s", e)
        _client = None
    return _client


async def chat_json(system: str, user: str, schema_hint: str = "") -> Optional[dict[str, Any]]:
    """Call the configured Azure OpenAI deployment and return parsed JSON.

    Returns ``None`` if no client is configured or the call fails — callers
    should then fall back to deterministic logic.
    """
    client = get_client()
    if client is None:
        return None
    try:
        scrubbed = redact(user)
        prompt = scrubbed if not schema_hint else f"{scrubbed}\n\nReturn ONLY valid JSON matching: {schema_hint}"
        resp = client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        text = resp.choices[0].message.content or "{}"
        return json.loads(text)
    except Exception as e:  # pragma: no cover
        log.warning("LLM call failed: %s", e)
        return None
