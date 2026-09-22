import unittest
from dataclasses import FrozenInstanceError
from unittest.mock import Mock

from backend.agent_fabric import (
    ActionRequest,
    Agent,
    AgentGroup,
    AgentRegistry,
    GovernanceDecision,
    Governor,
    Mission,
    Scheduler,
    Task,
    Worker,
    WorkerResult,
    WorkerState,
)


class RecordingGovernor:
    """Minimal governor double used to isolate workers and schedulers."""

    def __init__(self, error=None):
        self.error = error
        self.requests = []

    def authorize(self, request):
        self.requests.append(request)
        if self.error is not None:
            raise self.error


class AgentFabricModelTests(unittest.TestCase):
    def test_collection_defaults_are_not_shared(self):
        first_task = Task("t1", "m1", "code")
        second_task = Task("t2", "m1", "code")
        first_result = WorkerResult("t1", WorkerState.SUCCEEDED)
        second_result = WorkerResult("t2", WorkerState.SUCCEEDED)

        self.assertIsNot(first_task.input, second_task.input)
        self.assertIsNot(first_result.output, second_result.output)
        self.assertEqual(first_task.input, {})
        self.assertEqual(first_result.evidence, ())

    def test_models_are_frozen_value_objects(self):
        agent = Agent("coder-1", "Coder")

        with self.assertRaises(FrozenInstanceError):
            agent.enabled = False


class AgentRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = AgentRegistry()

    def test_register_agent_returns_agent_and_preserves_order(self):
        first = Agent("planner-1", "Planner", frozenset({"plan"}))
        second = Agent("coder-1", "Coder", frozenset({"code"}))

        self.assertIs(self.registry.register_agent(first), first)
        self.registry.register_agent(second)

        self.assertEqual(self.registry.agents(), (first, second))
        self.assertIs(self.registry.get_agent("planner-1"), first)

    def test_register_agent_rejects_non_positive_concurrency(self):
        for concurrency in (0, -1):
            with self.subTest(concurrency=concurrency):
                with self.assertRaisesRegex(
                    ValueError, "max_concurrency must be >= 1"
                ):
                    self.registry.register_agent(
                        Agent("invalid", "Invalid", max_concurrency=concurrency)
                    )

        self.assertEqual(self.registry.agents(), ())

    def test_register_group_assigns_membership_and_preserves_order(self):
        self.registry.register_agent(Agent("planner-1", "Planner"))
        self.registry.register_agent(Agent("coder-1", "Coder"))
        first = AgentGroup("core", "Core", ("planner-1", "coder-1"))
        second = AgentGroup("empty", "Empty")

        self.assertIs(self.registry.register_group(first), first)
        self.registry.register_group(second)

        self.assertEqual(self.registry.groups(), (first, second))
        self.assertIs(self.registry.get_group("core"), first)
        self.assertEqual(self.registry.get_agent("planner-1").group_id, "core")
        self.assertEqual(self.registry.get_agent("coder-1").group_id, "core")

    def test_register_group_rejects_unknown_agents_without_mutating_registry(self):
        original = Agent("planner-1", "Planner")
        self.registry.register_agent(original)

        with self.assertRaisesRegex(ValueError, r"unknown agents: \['missing'\]"):
            self.registry.register_group(
                AgentGroup("core", "Core", ("planner-1", "missing"))
            )

        self.assertEqual(self.registry.groups(), ())
        self.assertIs(self.registry.get_agent("planner-1"), original)

    def test_route_prefers_capacity_then_descending_agent_id(self):
        self.registry.register_agent(
            Agent("small", "Small", frozenset({"code"}), max_concurrency=1)
        )
        self.registry.register_agent(
            Agent("alpha", "Alpha", frozenset({"code"}), max_concurrency=2)
        )
        self.registry.register_agent(
            Agent("beta", "Beta", frozenset({"code"}), max_concurrency=2)
        )

        self.assertEqual(self.registry.route("code").id, "beta")

    def test_route_ignores_disabled_agents(self):
        self.registry.register_agent(
            Agent("disabled", "Disabled", frozenset({"code"}), enabled=False)
        )
        self.registry.register_agent(
            Agent("enabled", "Enabled", frozenset({"code"}))
        )

        self.assertEqual(self.registry.route("code").id, "enabled")

    def test_group_route_does_not_select_agents_outside_group(self):
        self.registry.register_agent(
            Agent("planner-1", "Planner", frozenset({"plan"}))
        )
        self.registry.register_agent(
            Agent("coder-1", "Coder", frozenset({"code"}))
        )
        self.registry.register_group(AgentGroup("core", "Core", ("planner-1",)))

        with self.assertRaisesRegex(
            LookupError, "no enabled agent for capability: code"
        ):
            self.registry.route("code", "core")

    def test_route_rejects_disabled_group(self):
        self.registry.register_group(
            AgentGroup("disabled", "Disabled", enabled=False)
        )

        with self.assertRaisesRegex(LookupError, "disabled group: disabled"):
            self.registry.route("code", "disabled")

    def test_route_reports_missing_capability(self):
        with self.assertRaisesRegex(
            LookupError, "no enabled agent for capability: review"
        ):
            self.registry.route("review")


class GovernorTests(unittest.TestCase):
    EXPECTED_HIGH_IMPACT = frozenset(
        {
            "credential_change",
            "deploy",
            "destructive_operation",
            "financial_action",
            "ownership_change",
            "production_change",
        }
    )

    def setUp(self):
        self.governor = Governor()

    def test_high_impact_catalog_covers_documented_actions(self):
        self.assertEqual(self.governor.HIGH_IMPACT, self.EXPECTED_HIGH_IMPACT)

    def test_low_risk_action_is_allowed_at_autonomy_boundaries(self):
        for autonomy_level in (0, 5):
            with self.subTest(autonomy_level=autonomy_level):
                request = ActionRequest("compute", autonomy_level=autonomy_level)
                self.assertIs(
                    self.governor.evaluate(request), GovernanceDecision.ALLOW
                )

    def test_out_of_range_autonomy_is_denied_even_when_approved(self):
        for autonomy_level in (-1, 6):
            with self.subTest(autonomy_level=autonomy_level):
                request = ActionRequest(
                    "deploy", autonomy_level=autonomy_level, approved=True
                )
                self.assertIs(
                    self.governor.evaluate(request), GovernanceDecision.DENY
                )

    def test_high_impact_action_requires_explicit_approval(self):
        request = ActionRequest("deploy")

        self.assertIs(
            self.governor.evaluate(request),
            GovernanceDecision.APPROVAL_REQUIRED,
        )
        with self.assertRaisesRegex(
            PermissionError, "approval required for action: deploy"
        ):
            self.governor.authorize(request)

    def test_approved_high_impact_action_is_allowed(self):
        request = ActionRequest("credential_change", approved=True)

        self.assertIs(
            self.governor.evaluate(request), GovernanceDecision.ALLOW
        )
        self.assertIsNone(self.governor.authorize(request))

    def test_critical_risk_requires_approval_for_ordinary_action(self):
        request = ActionRequest("compute", risk="critical")

        self.assertIs(
            self.governor.evaluate(request),
            GovernanceDecision.APPROVAL_REQUIRED,
        )

    def test_authorize_raises_specific_error_for_denied_action(self):
        with self.assertRaisesRegex(
            PermissionError, "action denied: compute"
        ):
            self.governor.authorize(
                ActionRequest("compute", autonomy_level=6, approved=True)
            )


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.agent = Agent("coder-1", "Coder", frozenset({"code"}))

    def test_success_includes_output_identity_and_evidence(self):
        governor = RecordingGovernor()
        handler = Mock(return_value={"value": 4})
        task = Task(
            "t1",
            "m1",
            "code",
            {"action": "compute", "autonomy_level": 5, "approved": True},
            risk="high",
        )

        result = Worker("worker-t1", self.agent, handler, governor).run(task)

        self.assertIs(result.state, WorkerState.SUCCEEDED)
        self.assertEqual(result.output, {"value": 4})
        self.assertEqual(result.worker_id, "worker-t1")
        self.assertEqual(
            result.evidence,
            (
                {
                    "type": "worker_result",
                    "worker_id": "worker-t1",
                    "task_id": "t1",
                    "agent_id": "coder-1",
                },
            ),
        )
        handler.assert_called_once_with(task)
        self.assertEqual(
            governor.requests,
            [
                ActionRequest(
                    action="compute",
                    risk="high",
                    autonomy_level=5,
                    approved=True,
                )
            ],
        )

    def test_missing_governance_inputs_use_safe_defaults(self):
        governor = RecordingGovernor()
        task = Task("t1", "m1", "code")

        Worker("worker-t1", self.agent, lambda unused: {}, governor).run(task)

        self.assertEqual(governor.requests, [ActionRequest(action="compute")])

    def test_permission_error_blocks_without_calling_handler(self):
        governor = RecordingGovernor(PermissionError("approval required"))
        handler = Mock(return_value={"should_not": "run"})

        result = Worker("worker-t1", self.agent, handler, governor).run(
            Task("t1", "m1", "code")
        )

        self.assertIs(result.state, WorkerState.BLOCKED)
        self.assertEqual(result.error, "approval required")
        self.assertEqual(result.output, {})
        self.assertEqual(result.evidence, ())
        handler.assert_not_called()

    def test_handler_exception_is_returned_as_failed_result(self):
        handler = Mock(side_effect=RuntimeError("adapter unavailable"))

        result = Worker(
            "worker-t1", self.agent, handler, RecordingGovernor()
        ).run(Task("t1", "m1", "code"))

        self.assertIs(result.state, WorkerState.FAILED)
        self.assertEqual(result.error, "adapter unavailable")
        self.assertEqual(result.worker_id, "worker-t1")

    def test_invalid_autonomy_input_is_returned_as_failed_result(self):
        result = Worker(
            "worker-t1", self.agent, Mock(), RecordingGovernor()
        ).run(Task("t1", "m1", "code", {"autonomy_level": "invalid"}))

        self.assertIs(result.state, WorkerState.FAILED)
        self.assertIn("invalid literal for int()", result.error)


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.registry = AgentRegistry()
        self.registry.register_agent(
            Agent("coder-1", "Coder", frozenset({"code"}))
        )
        self.registry.register_agent(
            Agent("planner-1", "Planner", frozenset({"plan"}), max_concurrency=2)
        )
        self.registry.register_group(
            AgentGroup("core", "Core", ("coder-1", "planner-1"))
        )
        self.scheduler = Scheduler(self.registry, RecordingGovernor())

    def test_dispatch_routes_executes_and_stores_result(self):
        task = Task("t1", "m1", "code", {"value": 3})

        result = self.scheduler.dispatch(
            task, lambda dispatched: {"value": dispatched.input["value"] + 1}
        )

        self.assertIs(result.state, WorkerState.SUCCEEDED)
        self.assertEqual(result.output, {"value": 4})
        self.assertIs(self.scheduler.results["t1"], result)

    def test_dispatch_enforces_concurrency_limit(self):
        nested_results = []

        def dispatch_while_active(unused):
            nested_results.append(
                self.scheduler.dispatch(
                    Task("nested", "m1", "code"), lambda task: {}
                )
            )
            return {"outer": "complete"}

        outer = self.scheduler.dispatch(
            Task("outer", "m1", "code"), dispatch_while_active
        )

        self.assertIs(outer.state, WorkerState.SUCCEEDED)
        self.assertEqual(len(nested_results), 1)
        self.assertIs(nested_results[0].state, WorkerState.BLOCKED)
        self.assertEqual(
            nested_results[0].error, "agent concurrency limit reached"
        )

    def test_dispatch_releases_capacity_after_handler_failure(self):
        failed = self.scheduler.dispatch(
            Task("failed", "m1", "code"),
            Mock(side_effect=RuntimeError("boom")),
        )
        retried = self.scheduler.dispatch(
            Task("retried", "m1", "code"), lambda task: {"ok": True}
        )

        self.assertIs(failed.state, WorkerState.FAILED)
        self.assertIs(retried.state, WorkerState.SUCCEEDED)

    def test_dispatch_respects_group_routing_boundary(self):
        outside = AgentRegistry()
        outside.register_agent(Agent("coder-1", "Coder", frozenset({"code"})))
        outside.register_group(AgentGroup("empty", "Empty"))
        scheduler = Scheduler(outside, RecordingGovernor())

        with self.assertRaisesRegex(
            LookupError, "no enabled agent for capability: code"
        ):
            scheduler.dispatch(
                Task("t1", "m1", "code"), lambda task: {}, "empty"
            )

    def test_run_mission_executes_tasks_in_order(self):
        calls = []
        mission = Mission(
            "m1",
            "Build a plan",
            (
                Task("plan", "m1", "plan"),
                Task("code", "m1", "code"),
            ),
        )
        handlers = {
            "plan": lambda task: calls.append(task.id) or {"planned": True},
            "code": lambda task: calls.append(task.id) or {"coded": True},
        }

        results = self.scheduler.run_mission(mission, handlers, "core")

        self.assertEqual(calls, ["plan", "code"])
        self.assertEqual(
            [result.state for result in results],
            [WorkerState.SUCCEEDED, WorkerState.SUCCEEDED],
        )

    def test_run_mission_stops_after_failed_task(self):
        second_handler = Mock(return_value={})
        mission = Mission(
            "m1",
            "Stop on failure",
            (
                Task("first", "m1", "code"),
                Task("second", "m1", "plan"),
            ),
        )

        results = self.scheduler.run_mission(
            mission,
            {
                "code": Mock(side_effect=RuntimeError("failed")),
                "plan": second_handler,
            },
        )

        self.assertEqual(len(results), 1)
        self.assertIs(results[0].state, WorkerState.FAILED)
        second_handler.assert_not_called()

    def test_run_mission_stops_when_handler_is_missing(self):
        later_handler = Mock(return_value={})
        mission = Mission(
            "m1",
            "Missing adapter",
            (
                Task("missing", "m1", "review"),
                Task("later", "m1", "code"),
            ),
        )

        results = self.scheduler.run_mission(mission, {"code": later_handler})

        self.assertEqual(len(results), 1)
        self.assertIs(results[0].state, WorkerState.FAILED)
        self.assertEqual(
            results[0].error, "no handler for capability: review"
        )
        later_handler.assert_not_called()

    def test_run_empty_mission_returns_empty_tuple(self):
        mission = Mission("m1", "Nothing to do")

        self.assertEqual(self.scheduler.run_mission(mission, {}), ())


class GovernedDispatchIntegrationTests(unittest.TestCase):
    def test_unapproved_high_impact_task_is_blocked_before_handler_runs(self):
        registry = AgentRegistry()
        registry.register_agent(
            Agent("coder-1", "Coder", frozenset({"code"}))
        )
        handler = Mock(return_value={"deployed": True})

        result = Scheduler(registry, Governor()).dispatch(
            Task("deploy", "m1", "code", {"action": "deploy"}), handler
        )

        self.assertIs(result.state, WorkerState.BLOCKED)
        self.assertEqual(result.error, "approval required for action: deploy")
        handler.assert_not_called()


if __name__ == "__main__":
    unittest.main()
