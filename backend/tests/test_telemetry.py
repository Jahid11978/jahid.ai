import unittest

from backend.telemetry.events import TelemetryEvent
from backend.telemetry.health import HealthRegistry
from backend.telemetry.metrics import MetricsRegistry
from backend.telemetry.redaction import redact
from backend.telemetry.tracing import TraceContext, trace


class TelemetryTests(unittest.TestCase):
    def test_event_has_correlation_id(self):
        event = TelemetryEvent(name="agent.started", source="agent-runtime")
        self.assertTrue(event.correlation_id)
        self.assertEqual(event.to_dict()["name"], "agent.started")

    def test_metrics_snapshot(self):
        metrics = MetricsRegistry()
        metrics.increment("agent.executions")
        metrics.observe("agent.latency_ms", 12.5)
        self.assertEqual(metrics.snapshot()["counters"]["agent.executions"], 1.0)

    def test_trace_context(self):
        with trace("trace-123") as context:
            self.assertEqual(context.trace_id, "trace-123")
            self.assertEqual(TraceContext.current().trace_id, "trace-123")

    def test_health(self):
        health = HealthRegistry()
        health.set("database", "healthy")
        self.assertEqual(health.overall(), "healthy")

    def test_redaction(self):
        result = redact({"token": "secret", "latency_ms": 10})
        self.assertEqual(result["token"], "[REDACTED]")
        self.assertEqual(result["latency_ms"], 10)


if __name__ == "__main__":
    unittest.main()
