from __future__ import annotations

SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "api_key",
    "access_token",
    "refresh_token",
}


def redact(attributes: dict) -> dict:
    """Return a shallow copy with values of top-level credential keys masked.

    Keys in ``SENSITIVE_KEYS`` match without regard to case. Nested values are
    unchanged. A key without ``lower()`` raises ``AttributeError``.
    """
    output = {}
    for key, value in attributes.items():
        if key.lower() in SENSITIVE_KEYS:
            output[key] = "[REDACTED]"
        else:
            output[key] = value
    return output
