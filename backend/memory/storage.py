from __future__ import annotations

from typing import Protocol

from .gateway import MemoryRecord, MemoryStore


class PostgresMemoryStore(MemoryStore, Protocol):
    """Contract for durable PostgreSQL memory storage."""


class RedisSessionStore(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None: ...
    async def delete(self, key: str) -> None: ...


class VectorMemoryStore(Protocol):
    async def upsert(self, record: MemoryRecord, embedding: list[float]) -> None: ...
    async def search(self, embedding: list[float], scope: str, limit: int = 10) -> list[MemoryRecord]: ...
    async def delete(self, memory_id: str) -> None: ...
