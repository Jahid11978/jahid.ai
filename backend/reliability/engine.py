from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from .models import Failure, RecoveryPlan, RecoveryStage
from .policy import RecoveryPolicy

logger = logging.getLogger(__name__)

Handler = Callable[[RecoveryPlan], Awaitable[dict[str, Any] | None]]


class MissingRecoveryHandler(RuntimeError):
    """Raised when an action stage has no registered implementation."""


class ReliabilityEngine:
    """Deterministic recovery coordinator with bounded retries and fail-closed execution."""

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
                if not await self._try_run(stage, plan):
                    return self._escalate(plan, stage)
                plan.completed.append(stage)
                continue

            if stage == RecoveryStage.RECOVER:
                succeeded = False
                for attempt in range(1, plan.max_attempts + 1):
                    plan.attempt = attempt
                    try:
                        await self._run_required(stage, plan)
                        succeeded = True
                        break
                    except Exception:
                        logger.exception(
                            "Recovery attempt failed: %s/%s",
                            attempt,
                            plan.max_attempts,
                        )
                        if attempt < plan.max_attempts:
                            await asyncio.sleep(min(2 ** (attempt - 1), 8))

                if not succeeded:
                    if await self._try_run(RecoveryStage.ROLLBACK, plan):
                        plan.completed.append(RecoveryStage.ROLLBACK)
                    else:
                        self._escalate(plan, RecoveryStage.ROLLBACK)
                    return plan

                plan.completed.append(stage)
                continue

            if stage == RecoveryStage.VERIFY:
                try:
                    result = await self._run_required(stage, plan)
                except MissingRecoveryHandler:
                    return self._escalate(plan, stage)

                plan.verification = result or {}
                if plan.verification.get("healthy") is True:
                    plan.completed.append(stage)
                    continue
                if plan.verification.get("healthy") is False:
                    if await self._try_run(RecoveryStage.ROLLBACK, plan):
                        plan.completed.append(RecoveryStage.ROLLBACK)
                    else:
                        self._escalate(plan, RecoveryStage.ROLLBACK)
                    return plan

                # Missing or malformed verification must never be treated as healthy.
                self._escalate(plan, stage)
                return plan

            if stage == RecoveryStage.RESUME:
                if not await self._try_run(stage, plan):
                    return self._escalate(plan, stage)
                plan.completed.append(stage)
                continue

            if not await self._try_run(stage, plan):
                return self._escalate(plan, stage)
            plan.completed.append(stage)

        return plan

    async def _run_required(
        self,
        stage: RecoveryStage,
        plan: RecoveryPlan,
    ) -> dict[str, Any] | None:
        handler = self.handlers.get(stage)
        if handler is None:
            raise MissingRecoveryHandler(f"No handler registered for {stage.value}")
        return await handler(plan)

    async def _try_run(self, stage: RecoveryStage, plan: RecoveryPlan) -> bool:
        try:
            await self._run_required(stage, plan)
            return True
        except MissingRecoveryHandler:
            logger.error("No recovery handler registered for %s", stage.value)
            return False
        except Exception:
            logger.exception("Recovery handler failed for %s", stage.value)
            return False

    @staticmethod
    def _escalate(plan: RecoveryPlan, failed_stage: RecoveryStage) -> RecoveryPlan:
        logger.error("Recovery escalated because %s could not complete safely", failed_stage.value)
        if not plan.completed or plan.completed[-1] != RecoveryStage.ESCALATE:
            plan.completed.append(RecoveryStage.ESCALATE)
        return plan
