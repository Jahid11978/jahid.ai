from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Protocol
from uuid import uuid4


class MemoryType(StrEnum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    PROJECT = "project"
    AGENT = "agent"
    KNOWLEDGE = "knowledge"
    ARCHIVE = "archive"


class MemoryScope(StrEnum):
    USER = "user"
    PROJECT = "project"
    AGENT = "agent"
    SYSTEM = "system"


@dataclass(slots=True)
class MemoryRecord:
    memory_id: str
    content: str
    type: MemoryType
    scope: str
    source: str
    actor: str
    agent: str | None = None
    project: str | None = None
    confidence: float = 1.0
    classification: str = "internal"
    retention_policy: str = "standard"
    approved: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MemoryPolicy(Protocol):
    def check_read(self, actor: str, scope: str) -> None: ...
    def check_write(self, actor: str, memory_type: MemoryType, scope: str) -> None: ...


class ProvenanceSink(Protocol):
    async def record(self, **event: Any) -> None: ...


class MemoryStore(Protocol):
    async def write(self, record: MemoryRecord) -> MemoryRecord: ...
    async def search(self, query: str, scope: str, limit: int = 10) -> list[MemoryRecord]: ...
    async def delete(self, memory_id: str) -> None: ...


class DenyByDefaultPolicy:
    """Secure default. Production IAM must be explicitly injected."""
    def check_read(self, actor: str, scope: str) -> None:
        raise PermissionError("memory read policy is not configured")

    def check_write(self, actor: str, memory_type: MemoryType, scope: str) -> None:
        raise PermissionError("memory write policy is not configured")


class AllowAllPolicy:
    """Explicit development/test policy. Never use as the production IAM policy."""
    def check_read(self, actor: str, scope: str) -> None:
        if not actor or not scope:
            raise PermissionError("actor and scope are required")

    def check_write(self, actor: str, memory_type: MemoryType, scope: str) -> None:
        if not actor or not scope:
            raise PermissionError("actor and scope are required")


class InMemoryStore:
    """Deterministic local adapter for tests and development."""
    def __init__(self) -> None:
        self._records: dict[str, MemoryRecord] = {}

    async def write(self, record: MemoryRecord) -> MemoryRecord:
        self._records[record.memory_id] = record
        return record

    async def search(self, query: str, scope: str, limit: int = 10) -> list[MemoryRecord]:
        terms = set(query.lower().split())
        matches = [r for r in self._records.values() if r.scope == scope and terms.intersection(r.content.lower().split())]
        return matches[:limit]

    async def delete(self, memory_id: str) -> None:
        self._records.pop(memory_id, None)


class MemoryGateway:
    """Single entry point for all agent memory reads and writes."""
    def __init__(self, store: MemoryStore | None = None, policy: MemoryPolicy | None = None, provenance: ProvenanceSink | None = None) -> None:
        self.store = store or InMemoryStore()
        self.policy = policy or DenyByDefaultPolicy()
        self.provenance = provenance

    async def remember(self, actor: str, content: str, memory_type: MemoryType, scope: str, *, source: str = "agent", agent: str | None = None, project: str | None = None, confidence: float = 1.0, classification: str = "internal", retention_policy: str = "standard", approved: bool = False) -> MemoryRecord:
        self.policy.check_write(actor, memory_type, scope)
        if not content.strip():
            raise ValueError("memory content cannot be empty")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        record = MemoryRecord(str(uuid4()), content.strip(), memory_type, scope, source, actor, agent, project, confidence, classification, retention_policy, approved)
        saved = await self.store.write(record)
        if self.provenance:
            await self.provenance.record(action="write", actor=actor, memory_id=saved.memory_id, memory_type=memory_type.value, scope=scope)
        return saved

    async def recall(self, actor: str, query: str, scope: str, *, limit: int = 10) -> list[MemoryRecord]:
        self.policy.check_read(actor, scope)
        if not query.strip():
            return []
        records = await self.store.search(query, scope, limit)
        if self.provenance:
            await self.provenance.record(action="read", actor=actor, query=query, scope=scope, count=len(records))
        return records

    async def forget(self, actor: str, memory_id: str, scope: str) -> None:
        self.policy.check_read(actor, scope)
        await self.store.delete(memory_id)
        if self.provenance:
            await self.provenance.record(action="delete", actor=actor, memory_id=memory_id, scope=scope)
