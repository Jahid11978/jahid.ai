import ast
import contextlib
import io
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from subprocess import run
from sys import executable
from threading import Event, Thread
from unittest.mock import Mock, patch

from backend.agent_fabric import (
    ActionRequest,
    Agent,
    ApprovalDecision,
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


HIGH_IMPACT_ACTIONS = frozenset(
    {
        "deploy",
        "production_change",
        "credential_change",
        "financial_action",
        "destructive_operation",
        "ownership_change",
    }
)


def configured_governor():
    governor = Governor()
    governor.HIGH_IMPACT = HIGH_IMPACT_ACTIONS
    return governor


class ModelTests(unittest.TestCase):
    def test_model_defaults_are_independent(self):
        first_task = Task("task-1", "mission-1", "plan")
        second_task = Task("task-2", "mission-1", "plan")
        first_mission = Mission("mission-1", "Plan a release")
        second_mission = Mission("mission-2", "Review a release")
        first_result = WorkerResult("task-1", WorkerState.SUCCEEDED)
        second_result = WorkerResult("task-2", WorkerState.SUCCEEDED)

        self.assertIsNot(first_task.input, second_task.input)
        self.assertIsNot(first_mission.metadata, second_mission.metadata)
        self.assertIsNot(first_result.output, second_result.output)
        self.assertEqual(first_result.evidence, ())

    def test_models_are_immutable(self):
        agent = Agent("agent-1", "Agent")

        with self.assertRaises(FrozenInstanceError):
            agent.enabled = False

    def test_worker_states_have_stable_serialized_values(self):
        self.assertEqual(
            [state.value for state in WorkerState],
            ["idle", "running", "succeeded", "failed", "blocked"],
        )


class AgentRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = AgentRegistry()

    def test_register_agent_rejects_non_positive_concurrency(self):
        for concurrency in (0, -1):
            with self.subTest(concurrency=concurrency):
                with self.assertRaisesRegex(ValueError, "max_concurrency must be >= 1"):
                    self.registry.register_agent(
                        Agent("agent", "Agent", max_concurrency=concurrency)
                    )

    def test_agents_and_groups_preserve_registration_order(self):
        first = self.registry.register_agent(Agent("first", "First"))
        second = self.registry.register_agent(Agent("second", "Second"))
        group = self.registry.register_group(
            AgentGroup("group", "Group", ("first", "second"))
        )

        self.assertEqual(
            tuple(agent.id for agent in self.registry.agents()),
            (first.id, second.id),
        )
        self.assertEqual(self.registry.groups(), (group,))

    def test_register_group_rejects_unknown_agents_without_mutating_registry(self):
        self.registry.register_agent(Agent("known", "Known"))

        with self.assertRaisesRegex(ValueError, r"unknown agents: \['missing'\]"):
            self.registry.register_group(
                AgentGroup("group", "Group", ("known", "missing"))
            )

        self.assertEqual(self.registry.groups(), ())
        self.assertIsNone(self.registry.get_agent("known").group_id)

    def test_register_group_associates_agents_without_mutating_original_values(self):
        original = Agent("agent", "Agent", frozenset({"plan"}))
        self.registry.register_agent(original)

        self.registry.register_group(AgentGroup("group", "Group", ("agent",)))

        self.assertIsNone(original.group_id)
        self.assertEqual(self.registry.get_agent("agent").group_id, "group")

    def test_route_selects_highest_capacity_agent_then_id(self):
        self.registry.register_agent(
            Agent("small", "Small", frozenset({"plan"}), max_concurrency=1)
        )
        self.registry.register_agent(
            Agent("alpha", "Alpha", frozenset({"plan"}), max_concurrency=3)
        )
        self.registry.register_agent(
            Agent("omega", "Omega", frozenset({"plan"}), max_concurrency=3)
        )

        self.assertEqual(self.registry.route("plan").id, "omega")

    def test_route_is_limited_to_requested_group(self):
        self.registry.register_agent(
            Agent("inside", "Inside", frozenset({"code"}), max_concurrency=1)
        )
        self.registry.register_agent(
            Agent("outside", "Outside", frozenset({"code"}), max_concurrency=5)
        )
        self.registry.register_group(AgentGroup("core", "Core", ("inside",)))

        self.assertEqual(self.registry.route("code", "core").id, "inside")

    def test_route_ignores_disabled_agents(self):
        self.registry.register_agent(
            Agent("disabled", "Disabled", frozenset({"plan"}), enabled=False)
        )
        self.registry.register_agent(
            Agent("enabled", "Enabled", frozenset({"plan"}))
        )

        self.assertEqual(self.registry.route("plan").id, "enabled")

    def test_route_rejects_disabled_group(self):
        self.registry.register_agent(Agent("agent", "Agent", frozenset({"plan"})))
        self.registry.register_group(
            AgentGroup("disabled", "Disabled", ("agent",), enabled=False)
        )

        with self.assertRaisesRegex(LookupError, "disabled group: disabled"):
            self.registry.route("plan", "disabled")

    def test_route_reports_missing_enabled_capability(self):
        self.registry.register_agent(
            Agent("disabled", "Disabled", frozenset({"plan"}), enabled=False)
        )

        with self.assertRaisesRegex(
            LookupError, "no enabled agent for capability: plan"
        ):
            self.registry.route("plan")


class GovernorTests(unittest.TestCase):
    def setUp(self):
        self.governor = configured_governor()

    def test_governor_declares_all_high_impact_actions(self):
        self.assertEqual(
            getattr(Governor, "HIGH_IMPACT", None), HIGH_IMPACT_ACTIONS
        )

    def test_low_risk_action_is_allowed_at_autonomy_boundaries(self):
        for autonomy_level in (0, 5):
            with self.subTest(autonomy_level=autonomy_level):
                decision = self.governor.evaluate(
                    ActionRequest("compute", autonomy_level=autonomy_level)
                )
                self.assertIs(decision, GovernanceDecision.ALLOW)

    def test_out_of_range_autonomy_is_denied_even_when_action_is_approved(self):
        for autonomy_level in (-1, 6):
            with self.subTest(autonomy_level=autonomy_level):
                decision = self.governor.evaluate(
                    ActionRequest(
                        "deploy", autonomy_level=autonomy_level, approved=True
                    )
                )
                self.assertIs(decision, GovernanceDecision.DENY)

    def test_each_high_impact_action_requires_approval(self):
        for action in HIGH_IMPACT_ACTIONS:
            with self.subTest(action=action):
                self.assertIs(
                    self.governor.evaluate(ActionRequest(action)),
                    GovernanceDecision.APPROVAL_REQUIRED,
                )
                self.assertIs(
                    self.governor.evaluate(ActionRequest(action, approved=True)),
                    GovernanceDecision.ALLOW,
                )

    def test_critical_risk_requires_approval_for_other_actions(self):
        request = ActionRequest("compute", risk="critical")

        self.assertIs(
            self.governor.evaluate(request), GovernanceDecision.APPROVAL_REQUIRED
        )
        self.assertIs(
            self.governor.evaluate(
                ActionRequest("compute", risk="critical", approved=True)
            ),
            GovernanceDecision.ALLOW,
        )

    def test_authorize_reports_approval_requirement(self):
        with self.assertRaisesRegex(
            PermissionError, "approval required for action: deploy"
        ):
            self.governor.authorize(ActionRequest("deploy"))

    def test_authorize_reports_denied_action(self):
        with self.assertRaisesRegex(PermissionError, "action denied: compute"):
            self.governor.authorize(ActionRequest("compute", autonomy_level=6))


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.agent = Agent("coder", "Coder", frozenset({"code"}))

    def test_successful_run_returns_output_identity_and_evidence(self):
        worker = Worker(
            "worker-1",
            self.agent,
            lambda task: {"answer": task.input["value"] + 1},
            configured_governor(),
        )

        result = worker.run(Task("task-1", "mission-1", "code", {"value": 3}))

        self.assertIs(result.state, WorkerState.SUCCEEDED)
        self.assertEqual(result.output, {"answer": 4})
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

    def test_governance_block_prevents_handler_execution(self):
        handler = Mock(return_value={"ok": True})
        worker = Worker("worker-1", self.agent, handler, configured_governor())

        result = worker.run(
            Task("task-1", "mission-1", "code", {"action": "deploy"}, action="deploy")
        )

        self.assertIs(result.state, WorkerState.BLOCKED)
        self.assertEqual(result.error, "approval required for action: deploy")
        self.assertEqual(result.worker_id, "worker-1")
        handler.assert_not_called()

    def test_approved_high_impact_action_executes_handler(self):
        handler = Mock(return_value={"deployed": True})
        worker = Worker("worker-1", self.agent, handler, configured_governor())
        task = Task(
            "task-1",
            "mission-1",
            "code",
            {"action": "deploy", "approved": True},
            action="deploy",
            actor="operator",
            approval=ApprovalDecision("task-1", "deploy", "operator", True),
        )

        result = worker.run(task)

        self.assertIs(result.state, WorkerState.SUCCEEDED)
        self.assertEqual(result.output, {"deployed": True})
        handler.assert_called_once_with(task)

    def test_invalid_autonomy_prevents_handler_execution(self):
        handler = Mock(return_value={"ok": True})
        worker = Worker("worker-1", self.agent, handler, configured_governor())

        result = worker.run(
            Task("task-1", "mission-1", "code", {"autonomy_level": 6}, autonomy_level=6)
        )

        self.assertIs(result.state, WorkerState.BLOCKED)
        self.assertEqual(result.error, "action denied: compute")
        handler.assert_not_called()

    def test_payload_cannot_approve_high_impact_action(self):
        handler = Mock(return_value={"ok": True})
        worker = Worker("worker-1", self.agent, handler, configured_governor())

        result = worker.run(Task(
            "task-1", "mission-1", "code", {"approved": True, "autonomy_level": 2},
            action="deploy",
        ))

        self.assertIs(result.state, WorkerState.BLOCKED)
        handler.assert_not_called()

    def test_task_required_approval_is_bound_to_action_and_actor(self):
        handler = Mock(return_value={"ok": True})
        worker = Worker("worker-1", self.agent, handler, configured_governor())
        task = Task(
            "task-1", "mission-1", "code", requires_approval=True,
            actor="operator", approval=ApprovalDecision("other", "compute", "operator", True),
        )

        result = worker.run(task)

        self.assertIs(result.state, WorkerState.BLOCKED)
        handler.assert_not_called()

    def test_handler_exception_becomes_failed_result(self):
        def fail(_task):
            raise RuntimeError("adapter unavailable")

        result = Worker("worker-1", self.agent, fail, configured_governor()).run(
            Task("task-1", "mission-1", "code")
        )

        self.assertIs(result.state, WorkerState.FAILED)
        self.assertEqual(result.error, "adapter unavailable")
        self.assertEqual(result.worker_id, "worker-1")
        self.assertEqual(result.output, {})
        self.assertEqual(result.evidence, ())


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.registry = AgentRegistry()
        self.registry.register_agent(
            Agent("planner", "Planner", frozenset({"plan"}), max_concurrency=2)
        )
        self.registry.register_agent(Agent("coder", "Coder", frozenset({"code"})))
        self.registry.register_group(
            AgentGroup("core", "Core", ("planner", "coder"))
        )
        self.scheduler = Scheduler(self.registry, configured_governor())

    def test_dispatch_routes_task_and_stores_result(self):
        task = Task("task-1", "mission-1", "code", {"value": 3})

        result = self.scheduler.dispatch(
            task, lambda dispatched: {"value": dispatched.input["value"] + 1}, "core"
        )

        self.assertIs(result.state, WorkerState.SUCCEEDED)
        self.assertEqual(result.output, {"value": 4})
        self.assertEqual(result.worker_id, "worker-task-1")
        self.assertIs(self.scheduler.results["task-1"], result)

    def test_dispatch_enforces_concurrency_during_nested_execution(self):
        nested_results = []

        def dispatch_nested(_task):
            nested_results.append(
                self.scheduler.dispatch(
                    Task("nested", "mission-1", "code"), lambda task: {"ok": True}
                )
            )
            return {"outer": True}

        outer = self.scheduler.dispatch(
            Task("outer", "mission-1", "code"), dispatch_nested
        )

        self.assertIs(outer.state, WorkerState.SUCCEEDED)
        self.assertEqual(len(nested_results), 1)
        self.assertIs(nested_results[0].state, WorkerState.BLOCKED)
        self.assertEqual(
            nested_results[0].error, "agent concurrency limit reached"
        )

    def test_concurrent_dispatch_records_block_and_releases_capacity(self):
        started, release = Event(), Event()
        completed = []

        def handler(_task):
            started.set()
            release.wait()
            return {"ok": True}

        first = Thread(target=lambda: completed.append(self.scheduler.dispatch(
            Task("first", "mission-1", "code"), handler,
        )), daemon=True)
        first.start()
        try:
            self.assertTrue(started.wait(2))
            blocked = self.scheduler.dispatch(
                Task("blocked", "mission-1", "code"), handler,
            )
            self.assertIs(blocked.state, WorkerState.BLOCKED)
            self.assertIs(self.scheduler.results["blocked"], blocked)
        finally:
            release.set()
            first.join(2)
        self.assertFalse(first.is_alive())
        self.assertIs(completed[0].state, WorkerState.SUCCEEDED)
        retried = self.scheduler.dispatch(
            Task("retried", "mission-1", "code"), lambda _task: {"ok": True},
        )
        self.assertIs(retried.state, WorkerState.SUCCEEDED)

    def test_dispatch_releases_capacity_after_handler_failure(self):
        failed = self.scheduler.dispatch(
            Task("failed", "mission-1", "code"),
            lambda _task: (_ for _ in ()).throw(RuntimeError("failed")),
        )
        retried = self.scheduler.dispatch(
            Task("retried", "mission-1", "code"), lambda _task: {"ok": True}
        )

        self.assertIs(failed.state, WorkerState.FAILED)
        self.assertIs(retried.state, WorkerState.SUCCEEDED)

    def test_run_mission_executes_tasks_in_order(self):
        seen = []
        mission = Mission(
            "mission-1",
            "Plan and code",
            (
                Task("plan", "mission-1", "plan"),
                Task("code", "mission-1", "code"),
            ),
        )
        handlers = {
            "plan": lambda task: seen.append(task.id) or {"planned": True},
            "code": lambda task: seen.append(task.id) or {"coded": True},
        }

        results = self.scheduler.run_mission(mission, handlers, "core")

        self.assertEqual(seen, ["plan", "code"])
        self.assertEqual(
            tuple(result.state for result in results),
            (WorkerState.SUCCEEDED, WorkerState.SUCCEEDED),
        )

    def test_run_mission_stops_after_blocked_task(self):
        later_handler = Mock(return_value={"ok": True})
        mission = Mission(
            "mission-1",
            "Deploy and continue",
            (
                Task("deploy", "mission-1", "code", {"action": "deploy"}, action="deploy"),
                Task("later", "mission-1", "plan"),
            ),
        )

        results = self.scheduler.run_mission(
            mission,
            {"code": lambda _task: {"ok": True}, "plan": later_handler},
        )

        self.assertEqual(len(results), 1)
        self.assertIs(results[0].state, WorkerState.BLOCKED)
        later_handler.assert_not_called()

    def test_run_mission_stops_after_handler_failure(self):
        later_handler = Mock(return_value={"ok": True})
        mission = Mission(
            "mission-1",
            "Code and continue",
            (
                Task("code", "mission-1", "code"),
                Task("later", "mission-1", "plan"),
            ),
        )

        results = self.scheduler.run_mission(
            mission,
            {
                "code": lambda _task: (_ for _ in ()).throw(RuntimeError("boom")),
                "plan": later_handler,
            },
        )

        self.assertEqual(len(results), 1)
        self.assertIs(results[0].state, WorkerState.FAILED)
        self.assertEqual(results[0].error, "boom")
        later_handler.assert_not_called()

    def test_run_mission_reports_missing_handler_and_stops(self):
        later_handler = Mock(return_value={"ok": True})
        mission = Mission(
            "mission-1",
            "Unknown then plan",
            (
                Task("unknown", "mission-1", "review"),
                Task("later", "mission-1", "plan"),
            ),
        )

        results = self.scheduler.run_mission(mission, {"plan": later_handler})

        self.assertEqual(len(results), 1)
        self.assertIs(results[0].state, WorkerState.FAILED)
        self.assertEqual(results[0].error, "no handler for capability: review")
        self.assertIs(self.scheduler.results["unknown"], results[0])
        later_handler.assert_not_called()


class CommandLineTests(unittest.TestCase):
    def test_demo_prints_successful_result(self):
        stdout = io.StringIO()

        with patch.object(
            Governor, "HIGH_IMPACT", HIGH_IMPACT_ACTIONS, create=True
        ), contextlib.redirect_stdout(stdout):
            jahids.demo()

        self.assertEqual(
            ast.literal_eval(stdout.getvalue().strip()),
            {
                "state": "succeeded",
                "output": {"value": 42},
                "worker_id": "worker-demo-1",
            },
        )

    def test_demo_runs_outside_repository_root(self):
        script = Path(__file__).resolve().parents[2] / "scripts" / "jahids.py"
        result = run(
            [executable, str(script), "agent-demo"], cwd="/tmp",
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("'state': 'succeeded'", result.stdout)

    def test_main_dispatches_agent_demo_command(self):
        with patch.object(jahids, "demo") as demo, patch(
            "sys.argv", ["jahids", "agent-demo"]
        ):
            jahids.main()

        demo.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
