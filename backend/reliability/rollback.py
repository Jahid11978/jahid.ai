from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass(frozen=True)
class RollbackTarget:
    component: str
    revision: str
    reason: str


class RollbackManager:
    """Rollback coordinator. It never invents a revision and requires an approved target."""

    def __init__(self) -> None:
        self.targets: dict[str, RollbackTarget] = {}

    def register(self, target: RollbackTarget) -> None:
        self.targets[target.component] = target

    async def execute(
        self,
        component: str,
        executor: Callable[[RollbackTarget], Awaitable[None]],
    ) -> bool:
        target = self.targets.get(component)
        if target is None:
            return False
        await executor(target)
        return True
