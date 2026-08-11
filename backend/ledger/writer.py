from __future__ import annotations

import hashlib
import json
import threading
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def event_hash(event: dict[str, Any], previous_hash: str | None) -> str:
    payload = canonical({"event": event, "previous_hash": previous_hash})
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AuditLedger:
    """Thread-safe append-only hash chain.

    Persistence is deliberately injected. The in-memory chain is deterministic for tests;
    production adapters should persist each event and checkpoint atomically.
    """

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            previous = self._events[-1]["event_hash"] if self._events else None
            record = dict(event)
            record["sequence"] = len(self._events) + 1
            record["previous_event_hash"] = previous
            hash_input = {
                key: value
                for key, value in record.items()
                if key != "previous_event_hash"
            }
            record["event_hash"] = event_hash(hash_input, previous)
            self._events.append(record)
            return dict(record)

    def verify(self) -> bool:
        previous = None
        for record in self._events:
            if record["previous_event_hash"] != previous:
                return False
            if event_hash({k: v for k, v in record.items() if k not in {"event_hash", "previous_event_hash"}}, previous) != record["event_hash"]:
                return False
            previous = record["event_hash"]
        return True

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._events]

    @property
    def head(self) -> str | None:
        return self._events[-1]["event_hash"] if self._events else None
