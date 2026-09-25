from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RecoveryStage(str, Enum):
    DETECT = "detect"
    CLASSIFY = "classify"
    PROTECT = "protect"
    RECOVER = "recover"
    VERIFY = "verify"
    RESUME = "resume"
    ROLLBACK = "rollback"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class Failure:
    component: str
    category: str
    message: str
    severity: str = "medium"
    retryable: bool = True
    impact: str = "limited"
    metadata: dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RecoveryPlan:
    failure: Failure
    stages: list[RecoveryStage]
    requires_approval: bool = False
    max_attempts: int = 3
    attempt: int = 0
    completed: list[RecoveryStage] = field(default_factory=list)
    verification: dict[str, Any] = field(default_factory=dict)

    @property
    def terminal(self) -> bool:
        return bool(self.completed) and self.completed[-1] in {
            RecoveryStage.RESUME,
            RecoveryStage.ROLLBACK,
            RecoveryStage.ESCALATE,
        }
