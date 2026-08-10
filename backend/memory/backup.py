from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(slots=True)
class BackupArtifact:
    backend: str
    location: str
    checksum: str
    created_at: str
    verified: bool = False


class BackupRegistry:
    def __init__(self) -> None:
        self.artifacts: list[BackupArtifact] = []

    def register(self, backend: str, location: str, payload: bytes) -> BackupArtifact:
        artifact = BackupArtifact(backend, location, hashlib.sha256(payload).hexdigest(), datetime.now(timezone.utc).isoformat())
        self.artifacts.append(artifact)
        return artifact

    def verify(self, artifact: BackupArtifact, payload: bytes) -> bool:
        valid = hashlib.sha256(payload).hexdigest() == artifact.checksum
        artifact.verified = valid
        return valid
