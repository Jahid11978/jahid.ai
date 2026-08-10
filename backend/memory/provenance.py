from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class ProvenanceLog:
    """Append-only audit sink; production adapters can persist events in PostgreSQL."""
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def record(self, **event: Any) -> None:
        self.events.append({"timestamp": datetime.now(timezone.utc).isoformat(), **event})
