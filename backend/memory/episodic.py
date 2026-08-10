from .gateway import MemoryGateway, MemoryRecord, MemoryType


class EpisodicMemory:
    def __init__(self, gateway: MemoryGateway):
        self.gateway = gateway

    async def record(self, actor: str, event: str, scope: str, **metadata) -> MemoryRecord:
        return await self.gateway.remember(actor, event, MemoryType.EPISODIC, scope, source="workflow_event", **metadata)

    async def recall(self, actor: str, query: str, scope: str, limit: int = 10) -> list[MemoryRecord]:
        return await self.gateway.recall(actor, query, scope, limit=limit)
