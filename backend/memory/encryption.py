from __future__ import annotations

import base64
import hashlib
import hmac


class EncryptionBoundary:
    """Small application boundary; production keys must come from a secret manager."""
    def __init__(self, key: bytes):
        if len(key) < 32:
            raise ValueError("encryption key must be at least 32 bytes")
        self._key = key

    def protect(self, plaintext: str) -> str:
        # Deterministic integrity envelope for the interface. Replace with AES-GCM/KMS in production.
        payload = plaintext.encode()
        tag = hmac.new(self._key, payload, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(tag + payload).decode()

    def verify(self, protected: str) -> str:
        raw = base64.urlsafe_b64decode(protected.encode())
        tag, payload = raw[:32], raw[32:]
        expected = hmac.new(self._key, payload, hashlib.sha256).digest()
        if not hmac.compare_digest(tag, expected):
            raise ValueError("memory integrity verification failed")
        return payload.decode()
