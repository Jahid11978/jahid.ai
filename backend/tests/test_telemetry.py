import asyncio
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from uuid import UUID

from backend.telemetry import HealthRegistry, MetricsRegistry, TelemetryEvent, TraceContext
from backend.telemetry.redaction import redact
from backend.telemetry.tracing import trace


class TelemetryEventTests(unittest.TestCase):
    def test_defaults_create_distinct_utc_events(self):
        """Verify event defaults include unique IDs, UTC time, and separate attributes."""
        first = TelemetryEvent(name="agent.started", source="agent-runtime")
        second = TelemetryEvent(name="agent.started", source="agent-runtime")

        self.assertEqual(first.severity, "info")
        self.assertEqual(first.name, "agent.started")
        self.assertEqual(first.source, "agent-runtime")
        self.assertEqual(UUID(hex=first.correlation_id).hex, first.correlation_id)
        self.assertEqual(len(first.correlation_id), 32)
        self.assertNotEqual(first.correlation_id, second.correlation_id)
        self.assertEqual(datetime.fromisoformat(first.timestamp).tzinfo, timezone.utc)
        first.attributes["attempt"] = 1
        self.assertEqual(second.attributes, {})

    def test_explicit_fields_and_nested_attributes_are_serialized_independently(self):
        """Verify serialization preserves every field and copies nested attributes."""
        event = TelemetryEvent(
            name="workflow.finished", source="scheduler", severity="warning",
            trace_id="trace-1", actor_id="actor-1", agent_id="agent-1",
            workflow_id="workflow-1", memory_id="memory-1",
            correlation_id="correlation-1", timestamp="2026-01-01T00:00:00+00:00",
            attributes={"result": {"attempts": [1]}},
        )

        exported = event.to_dict()
        self.assertEqual(exported, {
            "name": "workflow.finished", "source": "scheduler", "severity": "warning",
            "trace_id": "trace-1", "actor_id": "actor-1", "agent_id": "agent-1",
            "workflow_id": "workflow-1", "memory_id": "memory-1",
            "correlation_id": "correlation-1", "timestamp": "2026-01-01T00:00:00+00:00",
            "attributes": {"result": {"attempts": [1]}},
        })
        exported["attributes"]["result"]["attempts"].append(2)
        self.assertEqual(event.attributes["result"]["attempts"], [1])

    def test_event_fields_cannot_be_reassigned(self):
        """Verify frozen events reject correlation ID reassignment."""
        event = TelemetryEvent(name="agent.started", source="agent-runtime")
        with self.assertRaises(FrozenInstanceError):
            event.correlation_id = "replacement"


class MetricsRegistryTests(unittest.TestCase):
    def test_counters_accumulate_and_samples_preserve_order(self):
        """Verify an empty registry accumulates counters and retains sample order."""
        metrics = MetricsRegistry()
        self.assertEqual(metrics.snapshot(), {"counters": {}, "samples": {}})
        metrics.increment("agent.executions")
        metrics.increment("agent.executions", 2.5)
        metrics.observe("agent.latency_ms", 12.5)
        metrics.observe("agent.latency_ms", 0.0)
        self.assertEqual(metrics.snapshot(), {
            "counters": {"agent.executions": 3.5},
            "samples": {"agent.latency_ms": [12.5, 0.0]},
        })

    def test_snapshot_does_not_expose_registry_storage(self):
        """Verify snapshot mutations and new registries leave stored metrics intact."""
        metrics = MetricsRegistry()
        metrics.increment("requests")
        metrics.observe("latency", 1.0)
        snapshot = metrics.snapshot()
        snapshot["counters"]["requests"] = 99
        snapshot["samples"]["latency"].append(99.0)
        self.assertEqual(metrics.snapshot(), {
            "counters": {"requests": 1.0}, "samples": {"latency": [1.0]},
        })
        self.assertEqual(MetricsRegistry().snapshot(), {"counters": {}, "samples": {}})

    def test_concurrent_updates_are_not_lost(self):
        """Verify concurrent workers retain every counter update and sample."""
        metrics = MetricsRegistry()

        def record_batch(_):
            """Record one hundred requests and latency samples for a worker."""
            for _ in range(100):
                metrics.increment("requests")
                metrics.observe("latency", 0.5)

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(record_batch, range(8)))
        snapshot = metrics.snapshot()
        self.assertEqual(snapshot["counters"]["requests"], 800.0)
        self.assertEqual(snapshot["samples"]["latency"], [0.5] * 800)


class HealthRegistryTests(unittest.TestCase):
    def test_empty_and_mixed_health_states(self):
        """Verify empty and mixed component statuses produce the expected health."""
        cases = [
            ((), "unknown"),
            (("healthy",), "healthy"),
            (("healthy", "unknown"), "degraded"),
            (("healthy", "degraded"), "degraded"),
            (("healthy", "unknown", "critical"), "critical"),
        ]
        for statuses, expected in cases:
            with self.subTest(statuses=statuses):
                registry = HealthRegistry()
                for index, status in enumerate(statuses):
                    registry.set(f"component-{index}", status)
                self.assertEqual(registry.overall(), expected)

    def test_rechecking_component_replaces_status_and_detail(self):
        """Verify rechecks replace status, clear stale detail, and record UTC time."""
        registry = HealthRegistry()
        registry.set("database", "critical", "connection lost")
        self.assertEqual(registry.overall(), "critical")
        self.assertEqual(registry.snapshot()["database"]["detail"], "connection lost")
        registry.set("database", "healthy")
        snapshot = registry.snapshot()
        self.assertEqual(set(snapshot), {"database"})
        self.assertEqual(snapshot["database"]["name"], "database")
        self.assertEqual(snapshot["database"]["status"], "healthy")
        self.assertIsNone(snapshot["database"]["detail"])
        self.assertEqual(registry.overall(), "healthy")
        self.assertEqual(datetime.fromisoformat(snapshot["database"]["checked_at"]).tzinfo, timezone.utc)

    def test_snapshot_mutations_do_not_change_health(self):
        """Verify snapshot edits cannot change registered components or health."""
        registry = HealthRegistry()
        registry.set("database", "healthy")
        snapshot = registry.snapshot()
        snapshot["database"]["status"] = "critical"
        snapshot["cache"] = {"status": "critical"}
        self.assertEqual(registry.overall(), "healthy")
        self.assertEqual(set(registry.snapshot()), {"database"})


class RedactionTests(unittest.TestCase):
    def test_all_sensitive_keys_are_redacted_case_insensitively(self):
        """Verify case-insensitive masking preserves safe fields and the input."""
        sensitive_keys = (
            "AUTHORIZATION", "COOKIE", "PASSWORD", "SECRET", "ToKeN",
            "API_KEY", "ACCESS_TOKEN", "REFRESH_TOKEN",
        )
        attributes = {key: f"value-for-{key}" for key in sensitive_keys}
        attributes["latency_ms"] = 10
        attributes["token_count"] = 3
        result = redact(attributes)
        for key in sensitive_keys:
            self.assertEqual(result[key], "[REDACTED]")
            self.assertEqual(attributes[key], f"value-for-{key}")
        self.assertEqual(result["latency_ms"], 10)
        self.assertEqual(result["token_count"], 3)
        self.assertIsNot(result, attributes)

    def test_empty_attributes_and_noncredential_values(self):
        """Verify redaction preserves empty mappings and safe falsy values."""
        self.assertEqual(redact({}), {})
        metadata = {"duration": 0, "success": False, "reason": None}
        self.assertEqual(redact(metadata), metadata)


class TraceContextTests(unittest.TestCase):
    def test_generated_trace_ids_are_unique(self):
        """Verify generated IDs are unique and an implicit trace activates its ID."""
        first = TraceContext.create().trace_id
        second = TraceContext.create().trace_id
        self.assertEqual(UUID(hex=first).hex, first)
        self.assertNotEqual(first, second)
        with trace() as context:
            self.assertEqual(TraceContext.current().trace_id, context.trace_id)
            self.assertEqual(UUID(hex=context.trace_id).hex, context.trace_id)

    def test_nested_traces_restore_parent_and_prior_context(self):
        """Verify nested trace exits restore the parent and clear the outer ID."""
        with trace("parent"):
            with trace("child"):
                self.assertEqual(TraceContext.current().trace_id, "child")
            self.assertEqual(TraceContext.current().trace_id, "parent")
        self.assertNotIn(TraceContext.current().trace_id, {"parent", "child"})

    def test_trace_context_restores_after_exception(self):
        """Verify a failing child trace restores its parent's active ID."""
        with trace("parent"):
            with self.assertRaisesRegex(RuntimeError, "failed"):
                with trace("child"):
                    raise RuntimeError("failed")
            self.assertEqual(TraceContext.current().trace_id, "parent")


class AsyncTraceContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_tasks_keep_their_own_trace_ids(self):
        """Verify overlapping async tasks retain their own active trace IDs."""
        entered = asyncio.Event()
        release = asyncio.Event()

        async def first_task():
            """Keep the first trace active until the second task releases it."""
            with trace("first"):
                entered.set()
                await release.wait()
                return TraceContext.current().trace_id

        async def second_task():
            """Release the waiting task and read the second trace after yielding."""
            await entered.wait()
            with trace("second"):
                self.assertEqual(TraceContext.current().trace_id, "second")
                release.set()
                await asyncio.sleep(0)
                return TraceContext.current().trace_id

        first, second = await asyncio.gather(first_task(), second_task())
        self.assertEqual((first, second), ("first", "second"))


if __name__ == "__main__":
    unittest.main()
