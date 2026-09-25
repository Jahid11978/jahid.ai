import pytest

from backend.reliability import Failure, RecoveryStage, ReliabilityEngine
from backend.reliability.health import HealthRecord, HealthRegistry
from backend.reliability.policy import RecoveryPolicy


def test_high_impact_recovery_requires_approval():
    plan = RecoveryPolicy().plan(Failure("payments", "external", "failed", severity="high", impact="financial"))
    assert plan.requires_approval is True
    assert RecoveryPolicy().can_execute(plan) is False


@pytest.mark.asyncio
async def test_retry_and_verify_then_resume():
    engine = ReliabilityEngine()
    attempts = 0

    async def recover(plan):
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise RuntimeError("transient")
        return None

    async def verify(plan):
        return {"healthy": True}

    engine.register(RecoveryStage.RECOVER, recover)
    engine.register(RecoveryStage.VERIFY, verify)
    plan = await engine.recover(Failure("worker", "timeout", "transient"))
    assert attempts == 2
    assert plan.completed[-1] is RecoveryStage.RESUME


def test_health_registry():
    registry = HealthRegistry()
    registry.set(HealthRecord("database", "healthy"))
    registry.set(HealthRecord("worker", "degraded"))
    assert registry.overall() == "degraded"
    assert registry.snapshot()["database"]["status"] == "healthy"
