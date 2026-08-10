from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class TelemetryEvent:
    """Structured event used to correlate platform activity without secrets."""

    name: str
    source: str
    severity: str = "info"
    trace_id: str | None = None
    actor_id: str | None = None
    agent_id: str | None = None
    workflow_id: str | None = None
    memory_id: str | None = None
    correlation_id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
