from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class HealthRecord:
    component: str
    status: str = "unknown"
    latency_ms: float | None = None
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class HealthRegistry:
    """Small in-process health registry; exporters can observe it later."""

    def __init__(self) -> None:
        self._records: dict[str, HealthRecord] = {}

    def set(self, record: HealthRecord) -> None:
        record.updated_at = datetime.now(timezone.utc)
        self._records[record.component] = record

    def get(self, component: str) -> HealthRecord | None:
        return self._records.get(component)

    def snapshot(self) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "status": record.status,
                "latency_ms": record.latency_ms,
                "message": record.message,
                "metadata": record.metadata,
                "updated_at": record.updated_at.isoformat(),
            }
            for name, record in self._records.items()
        }

    def overall(self) -> str:
        statuses = {r.status for r in self._records.values()}
        if "critical" in statuses:
            return "critical"
        if "degraded" in statuses:
            return "degraded"
        if statuses and statuses <= {"healthy"}:
            return "healthy"
        return "unknown"
