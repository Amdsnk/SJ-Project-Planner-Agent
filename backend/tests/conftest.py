"""Shared test fixtures.

The agents auto-degrade to deterministic logic when no Azure OpenAI creds are
present, so the suite runs fully offline. We still pin the env to be explicit
about that expectation.
"""
import os
import sys
from pathlib import Path

# Ensure `app...` imports resolve when running `pytest` from `backend/`.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Force the offline / deterministic path for all tests.
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "")
os.environ.setdefault("AZURE_OPENAI_API_KEY", "")
os.environ.setdefault("AZURE_OPENAI_DEPLOYMENT", "")
os.environ.setdefault("REDACT_PII", "true")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_only.db")
