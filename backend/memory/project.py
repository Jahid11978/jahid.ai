from .gateway import MemoryGateway, MemoryRecord, MemoryType


class ProjectMemory:
    def __init__(self, gateway: MemoryGateway):
        self.gateway = gateway

    async def remember(self, actor: str, content: str, project: str, scope: str, **metadata) -> MemoryRecord:
        return await self.gateway.remember(actor, content, MemoryType.PROJECT, scope, source="project_context", project=project, **metadata)
