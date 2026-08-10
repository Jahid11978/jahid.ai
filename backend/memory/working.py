from .gateway import MemoryGateway, MemoryRecord, MemoryType


class WorkingMemory:
    def __init__(self, gateway: MemoryGateway):
        self.gateway = gateway

    async def put(self, actor: str, content: str, scope: str, **metadata) -> MemoryRecord:
        return await self.gateway.remember(actor, content, MemoryType.WORKING, scope, source="working_context", **metadata)

    async def get(self, actor: str, query: str, scope: str, limit: int = 20) -> list[MemoryRecord]:
        return await self.gateway.recall(actor, query, scope, limit=limit)
