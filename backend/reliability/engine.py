from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from .models import Failure, RecoveryPlan, RecoveryStage
from .policy import RecoveryPolicy

logger = logging.getLogger(__name__)

Handler = Callable[[RecoveryPlan], Awaitable[dict[str, Any] | None]]


class ReliabilityEngine:
    """Deterministic recovery coordinator with bounded retries and verification."""

    def __init__(self, policy: RecoveryPolicy | None = None) -> None:
        self.policy = policy or RecoveryPolicy()
        self.handlers: dict[RecoveryStage, Handler] = {}

    def register(self, stage: RecoveryStage, handler: Handler) -> None:
        self.handlers[stage] = handler

    async def recover(
        self,
        failure: Failure,
        *,
        approval_token: str | None = None,
    ) -> RecoveryPlan:
        plan = self.policy.plan(failure)
        if not self.policy.can_execute(plan, approval_token):
            plan.completed.append(RecoveryStage.ESCALATE)
            return plan

        for stage in plan.stages:
            if stage in {RecoveryStage.DETECT, RecoveryStage.CLASSIFY}:
                plan.completed.append(stage)
                continue
            if stage == RecoveryStage.PROTECT:
                await self._run(stage, plan)
                plan.completed.append(stage)
                continue

            if stage == RecoveryStage.RECOVER:
                succeeded = False
                for attempt in range(1, plan.max_attempts + 1):
                    plan.attempt = attempt
                    try:
                        await self._run(stage, plan)
                        succeeded = True
                        break
                    except Exception:
                        logger.exception("Recovery attempt failed: %s/%s", attempt, plan.max_attempts)
                        await asyncio.sleep(min(2 ** (attempt - 1), 8))
                if not succeeded:
                    plan.completed.append(RecoveryStage.ROLLBACK)
                    await self._run(RecoveryStage.ROLLBACK, plan)
                    return plan
                plan.completed.append(stage)
                continue

            if stage == RecoveryStage.VERIFY:
                result = await self._run(stage, plan)
                plan.verification = result or {}
                if plan.verification.get("healthy") is False:
                    plan.completed.append(RecoveryStage.ROLLBACK)
                    await self._run(RecoveryStage.ROLLBACK, plan)
                    return plan
                plan.completed.append(stage)
                continue

            await self._run(stage, plan)
            plan.completed.append(stage)

        return plan

    async def _run(self, stage: RecoveryStage, plan: RecoveryPlan) -> dict[str, Any] | None:
        handler = self.handlers.get(stage)
        if handler is None:
            return None
        return await handler(plan)
