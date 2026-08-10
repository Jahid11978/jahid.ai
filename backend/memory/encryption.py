from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EncryptionBoundary:
    """AES-256-GCM boundary. Keys must come from an external secret manager."""
    def __init__(self, key: bytes):
        if len(key) != 32:
            raise ValueError("AES-256-GCM requires a 32-byte key")
        self._key = key

    def protect(self, plaintext: str, *, associated_data: bytes | None = None) -> str:
        nonce = os.urandom(12)
        ciphertext = AESGCM(self._key).encrypt(nonce, plaintext.encode(), associated_data)
        return base64.urlsafe_b64encode(nonce + ciphertext).decode()

    def verify(self, protected: str, *, associated_data: bytes | None = None) -> str:
        raw = base64.urlsafe_b64decode(protected.encode())
        if len(raw) < 13:
            raise ValueError("invalid encrypted memory payload")
        nonce, ciphertext = raw[:12], raw[12:]
        plaintext = AESGCM(self._key).decrypt(nonce, ciphertext, associated_data)
        return plaintext.decode()
