from __future__ import annotations

from .gateway import MemoryGateway, MemoryRecord
from .ranking import rank


class RetrievalPipeline:
    """Permission, search, metadata filtering, ranking and freshness boundary."""
    def __init__(self, gateway: MemoryGateway):
        self.gateway = gateway

    async def run(self, actor: str, query: str, scope: str, *, limit: int = 10, memory_types: set[str] | None = None) -> list[MemoryRecord]:
        records = await self.gateway.recall(actor, query, scope, limit=max(limit * 3, 20))
        if memory_types:
            records = [r for r in records if r.type.value in memory_types]
        return rank(records, query)[:limit]
