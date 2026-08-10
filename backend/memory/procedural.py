from .gateway import MemoryGateway, MemoryRecord, MemoryType


class ProceduralMemory:
    def __init__(self, gateway: MemoryGateway):
        self.gateway = gateway

    async def approve(self, actor: str, procedure: str, scope: str, **metadata) -> MemoryRecord:
        return await self.gateway.remember(actor, procedure, MemoryType.PROCEDURAL, scope, source="approved_workflow", approved=True, **metadata)

    async def find(self, actor: str, query: str, scope: str, limit: int = 10) -> list[MemoryRecord]:
        return [r for r in await self.gateway.recall(actor, query, scope, limit=limit) if r.type == MemoryType.PROCEDURAL and r.approved]
