import ast
import io
import unittest
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError
from unittest.mock import Mock, patch

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
from scripts import jahids


class AllowAllGovernor:
    """Minimal governor used to isolate execution tests from policy tests."""

    def authorize(self, request):
        return None


class AgentFabricModelTests(unittest.TestCase):
    def test_models_are_frozen(self):
        agent = Agent("planner-1", "Planner")
        task = Task("task-1", "mission-1", "plan")

        with self.assertRaises(FrozenInstanceError):
            agent.enabled = False
        with self.assertRaises(FrozenInstanceError):
            task.risk = "critical"

    def test_mapping_defaults_are_independent(self):
        first_task = Task("task-1", "mission-1", "plan")
        second_task = Task("task-2", "mission-1", "plan")
        first_mission = Mission("mission-1", "First")
        second_mission = Mission("mission-2", "Second")

        self.assertIsNot(first_task.input, second_task.input)
        self.assertIsNot(first_mission.metadata, second_mission.metadata)

    def test_worker_result_defaults_to_empty_output_and_evidence(self):
        result = WorkerResult("task-1", WorkerState.BLOCKED, error="blocked")

        self.assertEqual(result.output, {})
        self.assertEqual(result.evidence, ())
        self.assertIsNone(result.worker_id)


class AgentRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = AgentRegistry()

    def test_register_agent_rejects_non_positive_concurrency(self):
        for concurrency in (0, -1):
            with self.subTest(concurrency=concurrency):
                with self.assertRaisesRegex(ValueError, "max_concurrency must be >= 1"):
                    self.registry.register_agent(
                        Agent("planner", "Planner", max_concurrency=concurrency)
                    )

        self.assertEqual(self.registry.agents(), ())

    def test_register_group_rejects_unknown_agents_without_mutating_registry(self):
        self.registry.register_agent(Agent("planner", "Planner"))

        with self.assertRaisesRegex(ValueError, "unknown agents: \\['missing'\\]"):
            self.registry.register_group(
                AgentGroup("core", "Core", ("planner", "missing"))
            )

        self.assertEqual(self.registry.groups(), ())
        self.assertIsNone(self.registry.get_agent("planner").group_id)

    def test_register_group_associates_agents_and_preserves_order(self):
        planner = Agent("planner", "Planner", frozenset({"plan"}))
        coder = Agent("coder", "Coder", frozenset({"code"}))
        self.registry.register_agent(planner)
        self.registry.register_agent(coder)
        group = AgentGroup("core", "Core", ("planner", "coder"))

        self.assertIs(self.registry.register_group(group), group)
        self.assertEqual(
            tuple(agent.id for agent in self.registry.agents()),
            (planner.id, coder.id),
        )
        self.assertEqual(self.registry.groups(), (group,))
        self.assertEqual(self.registry.get_agent("planner").group_id, "core")
        self.assertEqual(self.registry.get_agent("coder").group_id, "core")

    def test_route_prefers_enabled_agent_with_greatest_capacity(self):
        self.registry.register_agent(
            Agent("small", "Small", frozenset({"code"}), max_concurrency=1)
        )
        self.registry.register_agent(
            Agent("large", "Large", frozenset({"code"}), max_concurrency=3)
        )
        self.registry.register_agent(
            Agent(
                "disabled",
                "Disabled",
                frozenset({"code"}),
                max_concurrency=10,
                enabled=False,
            )
        )

        self.assertEqual(self.registry.route("code").id, "large")

    def test_route_is_deterministic_when_capacities_match(self):
        self.registry.register_agent(
            Agent("agent-a", "A", frozenset({"code"}), max_concurrency=2)
        )
        self.registry.register_agent(
            Agent("agent-b", "B", frozenset({"code"}), max_concurrency=2)
        )

        self.assertEqual(self.registry.route("code").id, "agent-b")

    def test_group_routing_is_limited_to_group_members(self):
        self.registry.register_agent(Agent("outside", "Outside", frozenset({"code"})))
        self.registry.register_agent(Agent("inside", "Inside", frozenset({"code"})))
        self.registry.register_group(AgentGroup("core", "Core", ("inside",)))

        self.assertEqual(self.registry.route("code", "core").id, "inside")

    def test_moving_agent_to_new_group_removes_old_routing_membership(self):
        self.registry.register_agent(Agent("coder", "Coder", frozenset({"code"})))
        self.registry.register_group(AgentGroup("old", "Old", ("coder",)))

        self.registry.register_group(AgentGroup("new", "New", ("coder",)))

        self.assertEqual(self.registry.get_agent("coder").group_id, "new")
        self.assertEqual(self.registry.route("code", "new").id, "coder")
        with self.assertRaisesRegex(
            LookupError, "no enabled agent for capability: code"
        ):
            self.registry.route("code", "old")

    def test_disabled_group_cannot_route_tasks(self):
        self.registry.register_agent(Agent("coder", "Coder", frozenset({"code"})))
        self.registry.register_group(
            AgentGroup("paused", "Paused", ("coder",), enabled=False)
        )

        with self.assertRaisesRegex(LookupError, "disabled group: paused"):
            self.registry.route("code", "paused")

    def test_route_rejects_missing_capability(self):
        self.registry.register_agent(Agent("planner", "Planner", frozenset({"plan"})))

        with self.assertRaisesRegex(LookupError, "no enabled agent for capability: code"):
            self.registry.route("code")


class GovernorTests(unittest.TestCase):
    def setUp(self):
        self.governor = Governor()

    def test_low_risk_action_is_allowed(self):
        self.assertIs(
            self.governor.evaluate(ActionRequest("compute")),
            GovernanceDecision.ALLOW,
        )

    def test_each_high_impact_action_requires_approval(self):
        actions = (
            "deploy",
            "production_change",
            "credential_change",
            "financial_action",
            "destructive_operation",
            "ownership_change",
        )

        for action in actions:
            with self.subTest(action=action):
                self.assertIs(
                    self.governor.evaluate(ActionRequest(action)),
                    GovernanceDecision.APPROVAL_REQUIRED,
                )

    def test_approved_high_impact_action_is_allowed(self):
        decision = self.governor.evaluate(ActionRequest("deploy", approved=True))

        self.assertIs(decision, GovernanceDecision.ALLOW)

    def test_critical_risk_requires_approval_even_for_ordinary_action(self):
        decision = self.governor.evaluate(ActionRequest("compute", risk="critical"))

        self.assertIs(decision, GovernanceDecision.APPROVAL_REQUIRED)

    def test_invalid_autonomy_is_denied_even_when_approved(self):
        for autonomy_level in (-1, 6):
            with self.subTest(autonomy_level=autonomy_level):
                decision = self.governor.evaluate(
                    ActionRequest(
                        "deploy", autonomy_level=autonomy_level, approved=True
                    )
                )
                self.assertIs(decision, GovernanceDecision.DENY)

    def test_autonomy_boundaries_are_valid(self):
        for autonomy_level in (0, 5):
            with self.subTest(autonomy_level=autonomy_level):
                decision = self.governor.evaluate(
                    ActionRequest("compute", autonomy_level=autonomy_level)
                )
                self.assertIs(decision, GovernanceDecision.ALLOW)

    def test_authorize_reports_approval_and_denial_reasons(self):
        with self.assertRaisesRegex(
            PermissionError, "approval required for action: deploy"
        ):
            self.governor.authorize(ActionRequest("deploy"))

        with self.assertRaisesRegex(PermissionError, "action denied: compute"):
            self.governor.authorize(ActionRequest("compute", autonomy_level=6))


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.agent = Agent("coder", "Coder", frozenset({"code"}))
        self.task = Task("task-1", "mission-1", "code", {"value": 3})

    def test_successful_run_returns_output_and_traceable_evidence(self):
        handler = Mock(return_value={"value": 4})
        governor = Mock(spec=Governor)
        worker = Worker("worker-1", self.agent, handler, governor)

        result = worker.run(self.task)

        self.assertEqual(result.state, WorkerState.SUCCEEDED)
        self.assertEqual(result.output, {"value": 4})
        self.assertEqual(result.worker_id, "worker-1")
        self.assertEqual(
            result.evidence,
            (
                {
                    "type": "worker_result",
                    "worker_id": "worker-1",
                    "task_id": "task-1",
                    "agent_id": "coder",
                },
            ),
        )
        handler.assert_called_once_with(self.task)
        governor.authorize.assert_called_once_with(
            ActionRequest(
                action="compute",
                risk="low",
                autonomy_level=0,
                approved=False,
            )
        )

    def test_governance_failure_blocks_without_calling_handler(self):
        handler = Mock()
        governor = Mock(spec=Governor)
        governor.authorize.side_effect = PermissionError("approval required")
        worker = Worker("worker-1", self.agent, handler, governor)

        result = worker.run(self.task)

        self.assertEqual(result.state, WorkerState.BLOCKED)
        self.assertEqual(result.error, "approval required")
        self.assertEqual(result.worker_id, "worker-1")
        self.assertEqual(result.evidence, ())
        handler.assert_not_called()

    def test_handler_failure_is_returned_as_failed_result(self):
        def failing_handler(task):
            raise RuntimeError("adapter unavailable")

        worker = Worker("worker-1", self.agent, failing_handler, AllowAllGovernor())

        result = worker.run(self.task)

        self.assertEqual(result.state, WorkerState.FAILED)
        self.assertEqual(result.error, "adapter unavailable")
        self.assertEqual(result.worker_id, "worker-1")
        self.assertEqual(result.output, {})

    def test_malformed_autonomy_input_fails_before_handler_execution(self):
        handler = Mock()
        task = Task(
            "task-1",
            "mission-1",
            "code",
            {"autonomy_level": "not-an-integer"},
        )
        worker = Worker("worker-1", self.agent, handler, AllowAllGovernor())

        result = worker.run(task)

        self.assertEqual(result.state, WorkerState.FAILED)
        self.assertIn("invalid literal for int()", result.error)
        handler.assert_not_called()


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.registry = AgentRegistry()
        self.registry.register_agent(
            Agent("coder", "Coder", frozenset({"code"}), max_concurrency=1)
        )
        self.registry.register_agent(Agent("planner", "Planner", frozenset({"plan"})))
        self.registry.register_group(
            AgentGroup("core", "Core", ("coder", "planner"))
        )
        self.scheduler = Scheduler(self.registry, AllowAllGovernor())

    def test_dispatch_executes_and_stores_result(self):
        task = Task("task-1", "mission-1", "code", {"value": 3})

        result = self.scheduler.dispatch(
            task, lambda current: {"value": current.input["value"] + 1}, "core"
        )

        self.assertEqual(result.state, WorkerState.SUCCEEDED)
        self.assertEqual(result.output, {"value": 4})
        self.assertIs(self.scheduler.results["task-1"], result)

    def test_reentrant_dispatch_honors_concurrency_limit_and_recovers_capacity(self):
        nested_results = []

        def outer_handler(task):
            nested_results.append(
                self.scheduler.dispatch(
                    Task("nested", task.mission_id, "code"),
                    lambda current: {"nested": True},
                )
            )
            return {"outer": True}

        outer = self.scheduler.dispatch(
            Task("outer", "mission-1", "code"), outer_handler
        )
        after = self.scheduler.dispatch(
            Task("after", "mission-1", "code"), lambda task: {"after": True}
        )

        self.assertEqual(outer.state, WorkerState.SUCCEEDED)
        self.assertEqual(nested_results[0].state, WorkerState.BLOCKED)
        self.assertEqual(
            nested_results[0].error, "agent concurrency limit reached"
        )
        self.assertEqual(after.state, WorkerState.SUCCEEDED)

    def test_handler_failure_releases_agent_capacity(self):
        def failing_handler(task):
            raise RuntimeError("boom")

        failed = self.scheduler.dispatch(
            Task("failed", "mission-1", "code"), failing_handler
        )
        retried = self.scheduler.dispatch(
            Task("retried", "mission-1", "code"), lambda task: {"ok": True}
        )

        self.assertEqual(failed.state, WorkerState.FAILED)
        self.assertEqual(retried.state, WorkerState.SUCCEEDED)

    def test_run_mission_executes_tasks_in_order(self):
        calls = []
        mission = Mission(
            "mission-1",
            "Build a plan and implementation",
            (
                Task("plan-task", "mission-1", "plan"),
                Task("code-task", "mission-1", "code"),
            ),
        )

        results = self.scheduler.run_mission(
            mission,
            {
                "plan": lambda task: calls.append(task.id) or {"planned": True},
                "code": lambda task: calls.append(task.id) or {"coded": True},
            },
            "core",
        )

        self.assertEqual(calls, ["plan-task", "code-task"])
        self.assertEqual(
            tuple(result.state for result in results),
            (WorkerState.SUCCEEDED, WorkerState.SUCCEEDED),
        )

    def test_run_mission_stops_at_missing_handler(self):
        code_handler = Mock(return_value={"coded": True})
        mission = Mission(
            "mission-1",
            "Stop on failure",
            (
                Task("missing", "mission-1", "plan"),
                Task("not-run", "mission-1", "code"),
            ),
        )

        results = self.scheduler.run_mission(mission, {"code": code_handler})

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].state, WorkerState.FAILED)
        self.assertEqual(results[0].error, "no handler for capability: plan")
        code_handler.assert_not_called()

    def test_run_mission_stops_after_governance_block(self):
        class BlockingGovernor:
            def authorize(self, request):
                if request.action == "blocked-action":
                    raise PermissionError("blocked by policy")

        scheduler = Scheduler(self.registry, BlockingGovernor())
        handler = Mock(return_value={"ok": True})
        mission = Mission(
            "mission-1",
            "Stop on block",
            (
                Task(
                    "blocked",
                    "mission-1",
                    "code",
                    {"action": "blocked-action"},
                ),
                Task("not-run", "mission-1", "code"),
            ),
        )

        results = scheduler.run_mission(mission, {"code": handler})

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].state, WorkerState.BLOCKED)
        handler.assert_not_called()


class AgentDemoTests(unittest.TestCase):
    def test_demo_prints_successful_result(self):
        stdout = io.StringIO()

        with patch.object(jahids, "Governor", return_value=AllowAllGovernor()):
            with redirect_stdout(stdout):
                jahids.demo()

        payload = ast.literal_eval(stdout.getvalue().strip())
        self.assertEqual(
            payload,
            {
                "state": "succeeded",
                "output": {"value": 42},
                "worker_id": "worker-demo-1",
            },
        )

    def test_main_dispatches_agent_demo_command(self):
        with patch.object(jahids, "demo") as demo:
            with patch("sys.argv", ["jahids", "agent-demo"]):
                jahids.main()

        demo.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
