from .gateway import MemoryGateway


class MemoryDeletion:
    def __init__(self, gateway: MemoryGateway):
        self.gateway = gateway

    async def forget(self, actor: str, memory_id: str, scope: str) -> None:
        await self.gateway.forget(actor, memory_id, scope)
