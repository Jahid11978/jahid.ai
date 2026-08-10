from __future__ import annotations

from .gateway import MemoryGateway, MemoryRecord
from .retention import is_expired


class MemoryLifecycle:
    def __init__(self, gateway: MemoryGateway):
        self.gateway = gateway

    async def purge_expired(self, actor: str, records: list[MemoryRecord], scope: str) -> int:
        removed = 0
        for record in records:
            if record.scope == scope and is_expired(record.created_at, record.retention_policy):
                await self.gateway.forget(actor, record.memory_id, scope)
                removed += 1
        return removed
