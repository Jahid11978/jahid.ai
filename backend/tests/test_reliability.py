import unittest

from backend.reliability.circuit_breaker import CircuitBreaker
from backend.reliability.engine import ReliabilityEngine
from backend.reliability.health import HealthRecord, HealthRegistry
from backend.reliability.models import Failure, RecoveryStage
from backend.reliability.policy import RecoveryPolicy
from backend.reliability.rollback import RollbackManager, RollbackTarget


class ReliabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_high_impact_recovery_requires_approval(self):
        engine = ReliabilityEngine()
        failure = Failure(
            component="database",
            category="outage",
            message="database unavailable",
            severity="critical",
            impact="data-loss",
        )
        plan = await engine.recover(failure)
        self.assertEqual(plan.completed[-1], RecoveryStage.ESCALATE)

    async def test_healthy_verification_allows_resume(self):
        engine = ReliabilityEngine()

        async def recover(_plan):
            return {"recovered": True}

        async def verify(_plan):
            return {"healthy": True}

        async def resume(_plan):
            return {"resumed": True}

        engine.register(RecoveryStage.RECOVER, recover)
        engine.register(RecoveryStage.VERIFY, verify)
        engine.register(RecoveryStage.RESUME, resume)

        failure = Failure(
            component="worker",
            category="transient",
            message="worker stopped",
        )
        plan = await engine.recover(failure)
        self.assertEqual(plan.completed[-1], RecoveryStage.RESUME)
        self.assertTrue(plan.terminal)

    async def test_missing_verification_escalates(self):
        engine = ReliabilityEngine()

        async def recover(_plan):
            return {"recovered": True}

        engine.register(RecoveryStage.RECOVER, recover)
        failure = Failure(
            component="worker",
            category="transient",
            message="worker stopped",
        )
        plan = await engine.recover(failure)
        self.assertEqual(plan.completed[-1], RecoveryStage.ESCALATE)
        self.assertNotIn(RecoveryStage.RESUME, plan.completed)

    def test_policy_marks_non_retryable_as_approval_required(self):
        failure = Failure(
            component="security",
            category="policy",
            message="blocked action",
            retryable=False,
        )
        plan = RecoveryPolicy().plan(failure)
        self.assertTrue(plan.requires_approval)
        self.assertEqual(plan.max_attempts, 0)

    def test_health_registry(self):
        health = HealthRegistry()
        health.set(HealthRecord(component="database", status="healthy"))
        health.set(HealthRecord(component="worker", status="degraded"))
        self.assertEqual(health.overall(), "degraded")

    def test_circuit_breaker(self):
        breaker = CircuitBreaker(failure_threshold=2)
        breaker.failure()
        self.assertFalse(breaker.open)
        breaker.failure()
        self.assertTrue(breaker.open)
        breaker.success()
        self.assertFalse(breaker.open)

    async def test_rollback_requires_registered_target(self):
        manager = RollbackManager()
        called = []

        async def execute(target):
            called.append(target.revision)

        self.assertFalse(await manager.execute("api", execute))
        manager.register(RollbackTarget("api", "rev-1", "approved rollback"))
        self.assertTrue(await manager.execute("api", execute))
        self.assertEqual(called, ["rev-1"])


if __name__ == "__main__":
    unittest.main()
