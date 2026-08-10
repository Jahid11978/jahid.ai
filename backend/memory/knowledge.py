from .gateway import MemoryGateway, MemoryRecord, MemoryType


class KnowledgeMemory:
    def __init__(self, gateway: MemoryGateway):
        self.gateway = gateway

    async def add(self, actor: str, content: str, scope: str, confidence: float = 1.0, **metadata) -> MemoryRecord:
        return await self.gateway.remember(actor, content, MemoryType.KNOWLEDGE, scope, source="validated_research", confidence=confidence, **metadata)
