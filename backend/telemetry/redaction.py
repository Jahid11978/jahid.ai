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
    """Remove common credential fields before telemetry leaves the process."""
    output = {}
    for key, value in attributes.items():
        if key.lower() in SENSITIVE_KEYS:
            output[key] = "[REDACTED]"
        else:
            output[key] = value
    return output
