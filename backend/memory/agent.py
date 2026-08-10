from .gateway import MemoryGateway, MemoryRecord, MemoryType


class AgentMemory:
    def __init__(self, gateway: MemoryGateway):
        self.gateway = gateway

    async def remember(self, actor: str, content: str, agent: str, scope: str, **metadata) -> MemoryRecord:
        return await self.gateway.remember(actor, content, MemoryType.AGENT, scope, source="agent_context", agent=agent, **metadata)
