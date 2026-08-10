from datetime import datetime, timedelta, timezone

DEFAULT_RETENTION_DAYS = {
    "working": 1,
    "episodic": 90,
    "semantic": 3650,
    "procedural": 3650,
    "project": 730,
    "agent": 180,
    "knowledge": 3650,
    "archive": 3650,
}


def expires_at(created_at: str, policy: str, *, days: int | None = None) -> datetime:
    ttl = days if days is not None else DEFAULT_RETENTION_DAYS.get(policy, 365)
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    return created + timedelta(days=ttl)


def is_expired(created_at: str, policy: str, now: datetime | None = None) -> bool:
    return (now or datetime.now(timezone.utc)) >= expires_at(created_at, policy)
