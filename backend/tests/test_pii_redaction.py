"""PII redaction — applied before any LLM call."""
from app.services.pii_redaction import redact

# Build the email at runtime so the test file itself never contains a literal
# address that source-control / IDE auto-redactors might masquerade.
AT = chr(64)
EMAIL_TEXT = "Reach out to alice" + AT + "corp.example tomorrow."


def test_emails_are_replaced():
    out = redact(EMAIL_TEXT)
    assert "[EMAIL]" in out
    assert AT not in out


def test_phone_numbers_are_replaced():
    assert "[PHONE]" in redact("Call +65 9123 4567 if blocked.")


def test_singapore_nric_is_replaced():
    assert "[ID]" in redact("Vendor ID: S1234567A on file.")


def test_api_key_is_replaced():
    # 16+ alnum chars after the "sk_" prefix to satisfy the API-key regex.
    secret = "sk_ABCDEFGHIJKLMNOP1234567890"
    out = redact(f"Old key {secret} must rotate.")
    assert "[SECRET]" in out
    assert secret not in out


def test_safe_text_passes_through():
    msg = "Aman will deliver the deck by Friday."
    assert redact(msg) == msg


def test_empty_input_returns_empty_string():
    assert redact("") == ""
    assert redact(None) == ""  # type: ignore[arg-type]
