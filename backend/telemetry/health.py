from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class HealthStatus:
    name: str
    status: str = "unknown"
    detail: str | None = None
    checked_at: str | None = None


class HealthRegistry:
    """Central registry for component health used by the control plane."""

    def __init__(self) -> None:
        self._checks: dict[str, HealthStatus] = {}

    def set(self, name: str, status: str, detail: str | None = None) -> None:
        self._checks[name] = HealthStatus(
            name=name,
            status=status,
            detail=detail,
            checked_at=datetime.now(timezone.utc).isoformat(),
        )

    def snapshot(self) -> dict[str, dict[str, str | None]]:
        return {name: vars(value).copy() for name, value in self._checks.items()}

    def overall(self) -> str:
        statuses = [item.status for item in self._checks.values()]
        if not statuses:
            return "unknown"
        if any(status == "critical" for status in statuses):
            return "critical"
        if any(status in {"degraded", "unknown"} for status in statuses):
            return "degraded"
        return "healthy"
