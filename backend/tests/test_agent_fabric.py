import ast
import contextlib
import io
import unittest
from contextlib import redirect_stdout
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
    """Return a governor configured with the high-impact actions used by tests."""
    governor = Governor()
    governor.HIGH_IMPACT = HIGH_IMPACT_ACTIONS
    return governor


class ModelTests(unittest.TestCase):
    def test_model_defaults_are_independent(self):
        """Verify mutable defaults are separate for each model instance."""
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
        """Verify frozen agents reject field reassignment."""
        agent = Agent("agent-1", "Agent")

        with self.assertRaises(FrozenInstanceError):
            agent.enabled = False

    def test_worker_states_have_stable_serialized_values(self):
        """Verify worker state values retain their expected serialized names."""
        self.assertEqual(
            [state.value for state in WorkerState],
            ["idle", "running", "succeeded", "failed", "blocked"],
        )


class AgentRegistryTests(unittest.TestCase):
    def setUp(self):
        """Create an empty registry for each registry test."""
        self.registry = AgentRegistry()

    def test_register_agent_rejects_non_positive_concurrency(self):
        """Verify zero and negative concurrency limits are rejected."""
        for concurrency in (0, -1):
            with self.subTest(concurrency=concurrency):
                with self.assertRaisesRegex(ValueError, "max_concurrency must be >= 1"):
                    self.registry.register_agent(
                        Agent("agent", "Agent", max_concurrency=concurrency)
                    )

    def test_agents_and_groups_preserve_registration_order(self):
        """Verify registry listings preserve agent and group registration order."""
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
        """Verify unknown group members leave the registry unchanged."""
        self.registry.register_agent(Agent("known", "Known"))

        with self.assertRaisesRegex(ValueError, r"unknown agents: \['missing'\]"):
            self.registry.register_group(
                AgentGroup("group", "Group", ("known", "missing"))
            )

        self.assertEqual(self.registry.groups(), ())
        self.assertIsNone(self.registry.get_agent("known").group_id)

    def test_register_group_associates_agents_without_mutating_original_values(self):
        """Verify group assignment replaces the stored agent without changing the original."""
        original = Agent("agent", "Agent", frozenset({"plan"}))
        self.registry.register_agent(original)

        self.registry.register_group(AgentGroup("group", "Group", ("agent",)))

        self.assertIsNone(original.group_id)
        self.assertEqual(self.registry.get_agent("agent").group_id, "group")

    def test_route_selects_highest_capacity_agent_then_id(self):
        """Verify routing prefers higher capacity and breaks ties by descending ID."""
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
        """Verify routing stays within the requested group despite higher capacity elsewhere."""
        self.registry.register_agent(
            Agent("inside", "Inside", frozenset({"code"}), max_concurrency=1)
        )
        self.registry.register_agent(
            Agent("outside", "Outside", frozenset({"code"}), max_concurrency=5)
        )
        self.registry.register_group(AgentGroup("core", "Core", ("inside",)))

        self.assertEqual(self.registry.route("code", "core").id, "inside")

    def test_route_ignores_disabled_agents(self):
        """Verify disabled agents are excluded from capability routing."""
        self.registry.register_agent(
            Agent("disabled", "Disabled", frozenset({"plan"}), enabled=False)
        )
        self.registry.register_agent(
            Agent("enabled", "Enabled", frozenset({"plan"}))
        )

        self.assertEqual(self.registry.route("plan").id, "enabled")

    def test_route_rejects_disabled_group(self):
        """Verify routing through a disabled group raises a lookup error."""
        self.registry.register_agent(Agent("agent", "Agent", frozenset({"plan"})))
        self.registry.register_group(
            AgentGroup("disabled", "Disabled", ("agent",), enabled=False)
        )

        with self.assertRaisesRegex(LookupError, "disabled group: disabled"):
            self.registry.route("plan", "disabled")

    def test_route_reports_missing_enabled_capability(self):
        """Verify routing fails when no enabled agent offers the capability."""
        self.registry.register_agent(
            Agent("disabled", "Disabled", frozenset({"plan"}), enabled=False)
        )

        with self.assertRaisesRegex(
            LookupError, "no enabled agent for capability: plan"
        ):
            self.registry.route("plan")


class GovernorTests(unittest.TestCase):
    def setUp(self):
        """Create a governor with the expected high-impact actions for each test."""
        self.governor = configured_governor()

    def test_governor_declares_all_high_impact_actions(self):
        """Verify the governor declares the complete set of high-impact actions."""
        self.assertEqual(
            getattr(Governor, "HIGH_IMPACT", None), HIGH_IMPACT_ACTIONS
        )

    def test_low_risk_action_is_allowed_at_autonomy_boundaries(self):
        """Verify low-risk actions are allowed at both valid autonomy boundaries."""
        for autonomy_level in (0, 5):
            with self.subTest(autonomy_level=autonomy_level):
                decision = self.governor.evaluate(
                    ActionRequest("compute", autonomy_level=autonomy_level)
                )
                self.assertIs(decision, GovernanceDecision.ALLOW)

    def test_out_of_range_autonomy_is_denied_even_when_action_is_approved(self):
        """Verify approval cannot override an invalid autonomy level."""
        for autonomy_level in (-1, 6):
            with self.subTest(autonomy_level=autonomy_level):
                decision = self.governor.evaluate(
                    ActionRequest(
                        "deploy", autonomy_level=autonomy_level, approved=True
                    )
                )
                self.assertIs(decision, GovernanceDecision.DENY)

    def test_each_high_impact_action_requires_approval(self):
        """Verify every high-impact action is gated on explicit approval."""
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
        """Verify critical risk requires approval even for ordinary compute actions."""
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
        """Verify authorization reports a missing approval as a permission error."""
        with self.assertRaisesRegex(
            PermissionError, "approval required for action: deploy"
        ):
            self.governor.authorize(ActionRequest("deploy"))

    def test_authorize_reports_denied_action(self):
        """Verify authorization reports invalid autonomy as a denied action."""
        with self.assertRaisesRegex(PermissionError, "action denied: compute"):
            self.governor.authorize(ActionRequest("compute", autonomy_level=6))


class WorkerTests(unittest.TestCase):
    def setUp(self):
        """Create a coding agent for each worker execution test."""
        self.agent = Agent("coder", "Coder", frozenset({"code"}))

    def test_successful_run_returns_output_identity_and_evidence(self):
        """Verify successful execution preserves handler output and records worker evidence."""
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
        """Verify a governance rejection blocks execution without invoking the handler."""
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
        """Verify a matching approval permits a high-impact action to run."""
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
        """Verify invalid task autonomy blocks execution before the handler runs."""
        handler = Mock(return_value={"ok": True})
        worker = Worker("worker-1", self.agent, handler, configured_governor())

        result = worker.run(
            Task("task-1", "mission-1", "code", {"autonomy_level": 6}, autonomy_level=6)
        )

        self.assertIs(result.state, WorkerState.BLOCKED)
        self.assertEqual(result.error, "action denied: compute")
        handler.assert_not_called()

    def test_payload_cannot_approve_high_impact_action(self):
        """Verify input payload fields cannot grant approval for a high-impact action."""
        handler = Mock(return_value={"ok": True})
        worker = Worker("worker-1", self.agent, handler, configured_governor())

        result = worker.run(Task(
            "task-1", "mission-1", "code", {"approved": True, "autonomy_level": 2},
            action="deploy",
        ))

        self.assertIs(result.state, WorkerState.BLOCKED)
        handler.assert_not_called()

    def test_task_required_approval_is_bound_to_action_and_actor(self):
        """Verify an approval for another task cannot satisfy required approval."""
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
        """Verify handler exceptions become failed results with error and worker identity."""
        def fail(_task):
            """Raise an adapter error to exercise worker failure reporting."""
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
        """Create a scheduler with planner and coder agents in a shared group."""
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
        """Verify dispatch routes a task and stores its returned result by task ID."""
        task = Task("task-1", "mission-1", "code", {"value": 3})

        result = self.scheduler.dispatch(
            task, lambda dispatched: {"value": dispatched.input["value"] + 1}, "core"
        )

        self.assertIs(result.state, WorkerState.SUCCEEDED)
        self.assertEqual(result.output, {"value": 4})
        self.assertEqual(result.worker_id, "worker-task-1")
        self.assertIs(self.scheduler.results["task-1"], result)

    def test_dispatch_enforces_concurrency_during_nested_execution(self):
        """Verify nested dispatch is blocked while the selected agent is at capacity."""
        nested_results = []

        def dispatch_nested(_task):
            """Attempt a second dispatch while the outer task holds the agent capacity."""
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
        """Verify overlapping dispatch records a block and frees capacity after completion."""
        started, release = Event(), Event()
        completed = []

        def handler(_task):
            """Signal execution and hold agent capacity until the test releases it."""
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
        """Verify a failed handler releases capacity for the next dispatch."""
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
        """Verify mission tasks run in declared order and return successful results."""
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
        """Verify a blocked task stops the mission before later handlers run."""
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
        """Verify a handler failure stops the mission and preserves its error."""
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
        """Verify a missing handler stores a failed result and stops the mission."""
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
        """Verify the local demo prints the expected output, state, and worker ID."""
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
        """Verify the demo script can run from outside the repository directory."""
        script = Path(__file__).resolve().parents[2] / "scripts" / "jahids.py"
        result = run(
            [executable, str(script), "agent-demo"], cwd="/tmp",
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("'state': 'succeeded'", result.stdout)

    def test_main_dispatches_agent_demo_command(self):
        """Verify the command-line entry point invokes the requested demo."""
        with patch.object(jahids, "demo") as demo, patch(
            "sys.argv", ["jahids", "agent-demo"]
        ):
            jahids.main()

        demo.assert_called_once_with()



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


class BranchAgentRegistryTests(unittest.TestCase):
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


class BranchGovernorTests(unittest.TestCase):
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


class BranchWorkerTests(unittest.TestCase):
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
            autonomy_level="not-an-integer",
        )
        worker = Worker("worker-1", self.agent, handler, Governor())

        result = worker.run(task)

        self.assertEqual(result.state, WorkerState.FAILED)
        self.assertIn("not supported between instances", result.error)
        handler.assert_not_called()


class BranchSchedulerTests(unittest.TestCase):
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
                    action="blocked-action",
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
