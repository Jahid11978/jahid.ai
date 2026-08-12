from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()


def event_hash(event: dict[str, Any], previous_hash: str | None) -> str:
    body = {"event": event, "previous_hash": previous_hash}
    return "sha256:" + hashlib.sha256(canonical_json(body)).hexdigest()


@dataclass(frozen=True)
class ChainEvent:
    event_type: str
    environment: str
    actor: str
    payload: dict[str, Any]
    artifact_digest: str | None = None
    cloudflare_version_id: str | None = None


class EventChain:
    """In-memory primitive used by the controller; persist each event in PostgreSQL."""

    def __init__(self) -> None:
        self._events: list[tuple[ChainEvent, str | None, str]] = []

    def append(self, event: ChainEvent) -> str:
        previous = self._events[-1][2] if self._events else None
        digest = event_hash(asdict(event), previous)
        self._events.append((event, previous, digest))
        return digest

    def verify(self) -> bool:
        previous = None
        for event, stored_previous, stored_hash in self._events:
            if stored_previous != previous:
                return False
            if event_hash(asdict(event), previous) != stored_hash:
                return False
            previous = stored_hash
        return True
