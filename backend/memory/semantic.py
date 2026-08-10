from .gateway import MemoryGateway, MemoryRecord, MemoryType


class SemanticMemory:
    def __init__(self, gateway: MemoryGateway):
        self.gateway = gateway

    async def remember(self, actor: str, fact: str, scope: str, confidence: float = 1.0, **metadata) -> MemoryRecord:
        return await self.gateway.remember(actor, fact, MemoryType.SEMANTIC, scope, source="validated_fact", confidence=confidence, **metadata)

    async def search(self, actor: str, query: str, scope: str, limit: int = 10) -> list[MemoryRecord]:
        return await self.gateway.recall(actor, query, scope, limit=limit)
