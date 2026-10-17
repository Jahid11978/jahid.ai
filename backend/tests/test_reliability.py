import unittest

from backend.reliability.circuit_breaker import CircuitBreaker
from backend.reliability.engine import ReliabilityEngine
from backend.reliability.health import HealthRecord, HealthRegistry
from backend.reliability.models import Failure, RecoveryStage
from backend.reliability.policy import RecoveryPolicy
from backend.reliability.rollback import RollbackManager, RollbackTarget


class ReliabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_high_impact_recovery_requires_approval(self):
        """Verify high-impact recovery escalates without approval."""
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
        """Verify successful recovery and healthy verification allow resuming."""
        engine = ReliabilityEngine()

        async def protect(_plan):
            """Return a successful protection result for the recovery scenario."""
            return {"protected": True}

        async def recover(_plan):
            """Return a successful recovery result for the recovery scenario."""
            return {"recovered": True}

        async def verify(_plan):
            """Report the recovered component as healthy."""
            return {"healthy": True}

        async def resume(_plan):
            """Return a successful resume result after healthy verification."""
            return {"resumed": True}

        engine.register(RecoveryStage.PROTECT, protect)
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

    async def test_missing_protect_handler_escalates(self):
        """Verify missing protection escalates before recovery can run."""
        engine = ReliabilityEngine()
        failure = Failure(
            component="worker",
            category="transient",
            message="worker stopped",
        )
        plan = await engine.recover(failure)
        self.assertEqual(plan.completed[-1], RecoveryStage.ESCALATE)
        self.assertNotIn(RecoveryStage.RECOVER, plan.completed)

    async def test_missing_recovery_handler_escalates(self):
        """Verify missing recovery and rollback handlers lead to escalation."""
        engine = ReliabilityEngine()

        async def protect(_plan):
            """Return a successful protection result for the recovery scenario."""
            return {"protected": True}

        engine.register(RecoveryStage.PROTECT, protect)
        failure = Failure(
            component="worker",
            category="transient",
            message="worker stopped",
        )
        plan = await engine.recover(failure)
        self.assertEqual(plan.completed[-1], RecoveryStage.ESCALATE)
        self.assertNotIn(RecoveryStage.RECOVER, plan.completed)

    async def test_missing_verification_escalates(self):
        """Verify missing verification escalates without resuming."""
        engine = ReliabilityEngine()

        async def protect(_plan):
            """Return a successful protection result for the recovery scenario."""
            return {"protected": True}

        async def recover(_plan):
            """Return a successful recovery result for the recovery scenario."""
            return {"recovered": True}

        engine.register(RecoveryStage.PROTECT, protect)
        engine.register(RecoveryStage.RECOVER, recover)
        failure = Failure(
            component="worker",
            category="transient",
            message="worker stopped",
        )
        plan = await engine.recover(failure)
        self.assertEqual(plan.completed[-1], RecoveryStage.ESCALATE)
        self.assertNotIn(RecoveryStage.RESUME, plan.completed)

    async def test_unhealthy_verification_rolls_back_when_handler_exists(self):
        """Verify unhealthy recovery invokes the registered rollback handler."""
        engine = ReliabilityEngine()
        called = []

        async def protect(_plan):
            """Return a successful protection result for the recovery scenario."""
            return {"protected": True}

        async def recover(_plan):
            """Return a successful recovery result for the recovery scenario."""
            return {"recovered": True}

        async def verify(_plan):
            """Report the recovered component as unhealthy."""
            return {"healthy": False}

        async def rollback(_plan):
            """Record the rollback invocation and return a successful result."""
            called.append("rollback")
            return {"rolled_back": True}

        engine.register(RecoveryStage.PROTECT, protect)
        engine.register(RecoveryStage.RECOVER, recover)
        engine.register(RecoveryStage.VERIFY, verify)
        engine.register(RecoveryStage.ROLLBACK, rollback)

        failure = Failure(
            component="worker",
            category="transient",
            message="worker stopped",
        )
        plan = await engine.recover(failure)
        self.assertEqual(plan.completed[-1], RecoveryStage.ROLLBACK)
        self.assertEqual(called, ["rollback"])
        self.assertTrue(plan.terminal)

    def test_policy_marks_non_retryable_as_approval_required(self):
        """Verify non-retryable failures require approval and disable retries."""
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
        """Verify a degraded component makes overall health degraded."""
        health = HealthRegistry()
        health.set(HealthRecord(component="database", status="healthy"))
        health.set(HealthRecord(component="worker", status="degraded"))
        self.assertEqual(health.overall(), "degraded")

    def test_circuit_breaker(self):
        """Verify consecutive failures open the circuit and success resets it."""
        breaker = CircuitBreaker(failure_threshold=2)
        breaker.failure()
        self.assertFalse(breaker.open)
        breaker.failure()
        self.assertTrue(breaker.open)
        breaker.success()
        self.assertFalse(breaker.open)

    async def test_rollback_requires_registered_target(self):
        """Verify rollback executes only for a registered component revision."""
        manager = RollbackManager()
        called = []

        async def execute(target):
            """Record the revision passed to the rollback executor."""
            called.append(target.revision)

        self.assertFalse(await manager.execute("api", execute))
        manager.register(RollbackTarget("api", "rev-1", "approved rollback"))
        self.assertTrue(await manager.execute("api", execute))
        self.assertEqual(called, ["rev-1"])


if __name__ == "__main__":
    unittest.main()
