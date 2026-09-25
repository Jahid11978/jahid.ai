from __future__ import annotations

from .models import Failure, RecoveryPlan, RecoveryStage


class RecoveryPolicy:
    """Deny-by-default recovery policy.

    Recovery may automate low-impact, reversible actions. State-changing,
    destructive, security-sensitive, or externally visible actions require
    an explicit approval token from the existing control plane.
    """

    def plan(self, failure: Failure) -> RecoveryPlan:
        high_impact = failure.severity in {"high", "critical"} or failure.impact in {
            "data-loss", "security", "external", "financial"
        }
        if not failure.retryable:
            return RecoveryPlan(
                failure=failure,
                stages=[RecoveryStage.DETECT, RecoveryStage.CLASSIFY,
                        RecoveryStage.PROTECT, RecoveryStage.ESCALATE],
                requires_approval=True,
                max_attempts=0,
            )

        stages = [
            RecoveryStage.DETECT,
            RecoveryStage.CLASSIFY,
            RecoveryStage.PROTECT,
            RecoveryStage.RECOVER,
            RecoveryStage.VERIFY,
            RecoveryStage.RESUME,
        ]
        return RecoveryPlan(
            failure=failure,
            stages=stages,
            requires_approval=high_impact,
            max_attempts=3,
        )

    def can_execute(self, plan: RecoveryPlan, approval_token: str | None = None) -> bool:
        if not plan.requires_approval:
            return True
        return bool(approval_token)
