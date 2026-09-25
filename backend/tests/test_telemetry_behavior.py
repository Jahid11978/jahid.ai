import asyncio
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

from backend.telemetry import HealthRegistry, MetricsRegistry, TelemetryEvent, TraceContext
from backend.telemetry.redaction import redact
from backend.telemetry.tracing import trace


class TelemetryEventTests(unittest.TestCase):
    def test_defaults_are_unique_and_utc(self):
        first = TelemetryEvent(name="agent.started", source="agent-runtime")
        second = TelemetryEvent(name="agent.started", source="agent-runtime")

        self.assertEqual(first.severity, "info")
        self.assertIsNone(first.trace_id)
        self.assertEqual(first.attributes, {})
        self.assertRegex(first.correlation_id, r"^[0-9a-f]{32}$")
        self.assertNotEqual(first.correlation_id, second.correlation_id)
        self.assertEqual(datetime.fromisoformat(first.timestamp).tzinfo, timezone.utc)

    def test_serializes_explicit_context_and_attributes(self):
        event = TelemetryEvent(
            name="workflow.completed",
            source="scheduler",
            severity="warning",
            trace_id="trace-1",
            actor_id="actor-1",
            agent_id="agent-1",
            workflow_id="workflow-1",
            memory_id="memory-1",
            correlation_id="correlation-1",
            timestamp="2026-01-02T03:04:05+00:00",
            attributes={"duration_ms": 12.5},
        )

        self.assertEqual(event.to_dict(), {
            "name": "workflow.completed",
            "source": "scheduler",
            "severity": "warning",
            "trace_id": "trace-1",
            "actor_id": "actor-1",
            "agent_id": "agent-1",
            "workflow_id": "workflow-1",
            "memory_id": "memory-1",
            "correlation_id": "correlation-1",
            "timestamp": "2026-01-02T03:04:05+00:00",
            "attributes": {"duration_ms": 12.5},
        })

    def test_default_and_serialized_attributes_are_independent(self):
        first = TelemetryEvent(name="first", source="test")
        second = TelemetryEvent(name="second", source="test")
        first.attributes["nested"] = {"count": 1}
        serialized = first.to_dict()
        serialized["attributes"]["nested"]["count"] = 2

        self.assertEqual(first.attributes["nested"]["count"], 1)
        self.assertEqual(second.attributes, {})

    def test_fields_cannot_be_reassigned(self):
        event = TelemetryEvent(name="created", source="test")
        with self.assertRaises(FrozenInstanceError):
            event.name = "changed"


class MetricsRegistryTests(unittest.TestCase):
    def test_counters_accumulate_values_and_samples_keep_order(self):
        metrics = MetricsRegistry()
        metrics.increment("requests")
        metrics.increment("requests", 0.5)
        metrics.increment("requests", -0.25)
        metrics.observe("latency_ms", 0.0)
        metrics.observe("latency_ms", 12.5)

        self.assertEqual(metrics.snapshot(), {
            "counters": {"requests": 1.25},
            "samples": {"latency_ms": [0.0, 12.5]},
        })

    def test_empty_and_separate_registries(self):
        first = MetricsRegistry()
        second = MetricsRegistry()
        self.assertEqual(first.snapshot(), {"counters": {}, "samples": {}})

        first.increment("requests")
        first.observe("latency_ms", 3.0)
        self.assertEqual(second.snapshot(), {"counters": {}, "samples": {}})

    def test_snapshot_does_not_expose_mutable_internal_state(self):
        metrics = MetricsRegistry()
        metrics.increment("requests")
        metrics.observe("latency_ms", 3.0)
        snapshot = metrics.snapshot()
        snapshot["counters"]["requests"] = 99
        snapshot["samples"]["latency_ms"].append(99.0)

        self.assertEqual(metrics.snapshot(), {
            "counters": {"requests": 1.0},
            "samples": {"latency_ms": [3.0]},
        })

    def test_concurrent_increments_do_not_lose_updates(self):
        metrics = MetricsRegistry()
        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(metrics.increment, ["requests"] * 1000))

        self.assertEqual(metrics.snapshot()["counters"]["requests"], 1000.0)


class TraceContextTests(unittest.TestCase):
    def test_create_and_current_without_active_trace_generate_ids(self):
        created = TraceContext.create()
        current = TraceContext.current()
        self.assertRegex(created.trace_id, r"^[0-9a-f]{32}$")
        self.assertRegex(current.trace_id, r"^[0-9a-f]{32}$")
        self.assertNotEqual(created.trace_id, current.trace_id)

    def test_explicit_and_nested_traces_restore_prior_context(self):
        with trace("outer") as outer:
            self.assertEqual(outer.trace_id, TraceContext.current().trace_id)
            with trace("inner") as inner:
                self.assertEqual(inner.trace_id, "inner")
                self.assertEqual(TraceContext.current().trace_id, "inner")
            self.assertEqual(TraceContext.current().trace_id, "outer")

        self.assertNotEqual(TraceContext.current().trace_id, "outer")

    def test_implicit_trace_generates_an_id(self):
        with trace() as context:
            self.assertRegex(context.trace_id, r"^[0-9a-f]{32}$")
            self.assertEqual(TraceContext.current(), context)

    def test_trace_restores_context_when_body_raises(self):
        with trace("outer"):
            with self.assertRaisesRegex(RuntimeError, "failed"):
                with trace("inner"):
                    raise RuntimeError("failed")
            self.assertEqual(TraceContext.current().trace_id, "outer")


class AsyncTraceContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_tasks_keep_separate_trace_ids(self):
        async def worker(trace_id):
            with trace(trace_id):
                await asyncio.sleep(0)
                return TraceContext.current().trace_id

        self.assertEqual(await asyncio.gather(worker("first"), worker("second")),
                         ["first", "second"])
        self.assertNotIn(TraceContext.current().trace_id, {"first", "second"})


class HealthRegistryTests(unittest.TestCase):
    def test_empty_registry_is_unknown(self):
        health = HealthRegistry()
        self.assertEqual(health.overall(), "unknown")
        self.assertEqual(health.snapshot(), {})

    def test_status_aggregation_respects_severity(self):
        cases = [
            ({"database": "healthy", "cache": "healthy"}, "healthy"),
            ({"database": "healthy", "cache": "unknown"}, "degraded"),
            ({"database": "healthy", "cache": "degraded"}, "degraded"),
            ({"database": "critical", "cache": "degraded"}, "critical"),
            ({"database": "critical", "cache": "unknown"}, "critical"),
        ]
        for statuses, expected in cases:
            with self.subTest(statuses=statuses):
                health = HealthRegistry()
                for name, status in statuses.items():
                    health.set(name, status)
                self.assertEqual(health.overall(), expected)

    def test_set_replaces_existing_status_and_detail(self):
        health = HealthRegistry()
        health.set("database", "critical", "connection lost")
        health.set("database", "healthy")

        self.assertEqual(health.overall(), "healthy")
        self.assertEqual(len(health.snapshot()), 1)
        self.assertIsNone(health.snapshot()["database"]["detail"])

    def test_snapshot_has_utc_check_time_and_is_detached(self):
        health = HealthRegistry()
        health.set("database", "degraded", "slow queries")
        snapshot = health.snapshot()

        self.assertEqual(snapshot["database"]["name"], "database")
        self.assertEqual(snapshot["database"]["status"], "degraded")
        self.assertEqual(snapshot["database"]["detail"], "slow queries")
        self.assertEqual(datetime.fromisoformat(snapshot["database"]["checked_at"]).tzinfo,
                         timezone.utc)
        snapshot["database"]["status"] = "healthy"
        self.assertEqual(health.snapshot()["database"]["status"], "degraded")

    def test_registries_do_not_share_component_state(self):
        first = HealthRegistry()
        second = HealthRegistry()
        first.set("database", "healthy")
        self.assertEqual(second.snapshot(), {})
        self.assertEqual(second.overall(), "unknown")


class RedactionTests(unittest.TestCase):
    def test_sensitive_keys_are_redacted_case_insensitively(self):
        sensitive_keys = (
            "authorization", "cookie", "password", "secret", "token",
            "api_key", "access_token", "refresh_token",
        )
        attributes = {key.upper(): "credential" for key in sensitive_keys}
        attributes["latency_ms"] = 10

        result = redact(attributes)

        self.assertEqual(result, {
            **{key.upper(): "[REDACTED]" for key in sensitive_keys},
            "latency_ms": 10,
        })
        self.assertTrue(all(value == "credential" for key, value in attributes.items()
                            if key != "latency_ms"))

    def test_returns_a_new_mapping_for_empty_and_safe_inputs(self):
        for attributes in ({}, {"duration_ms": 12.5, "status": "ok"}):
            with self.subTest(attributes=attributes):
                result = redact(attributes)
                self.assertEqual(result, attributes)
                self.assertIsNot(result, attributes)


if __name__ == "__main__":
    unittest.main()
