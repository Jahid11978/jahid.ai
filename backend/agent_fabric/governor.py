from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any

class GovernanceDecision(str, Enum):
    ALLOW="allow"; APPROVAL_REQUIRED="approval_required"; DENY="deny"

@dataclass(frozen=True)
class ActionRequest:
    action: str
    risk: str = "low"
    autonomy_level: int = 0
    approved: bool = False
    actor: str = "system"
    metadata: dict[str, Any] | None = None

class Governor:
    def evaluate(self, request: ActionRequest) -> GovernanceDecision:
        if request.autonomy_level < 0 or request.autonomy_level > 5:
            return GovernanceDecision.DENY
        if request.action in self.HIGH_IMPACT or request.risk == "critical":
            return GovernanceDecision.ALLOW if request.approved else GovernanceDecision.APPROVAL_REQUIRED
        return GovernanceDecision.ALLOW
        return GovernanceDecision.ALLOW
    def authorize(self, request: ActionRequest) -> None:
        decision=self.evaluate(request)
        if decision is GovernanceDecision.APPROVAL_REQUIRED: raise PermissionError(f"approval required for action: {request.action}")
        if decision is GovernanceDecision.DENY: raise PermissionError(f"action denied: {request.action}")
