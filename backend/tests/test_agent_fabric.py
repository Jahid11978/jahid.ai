import unittest
from backend.agent_fabric import Agent,AgentGroup,AgentRegistry,Scheduler,Governor,Task
from backend.agent_fabric.models import WorkerState

class AgentFabricTests(unittest.TestCase):
    def setUp(self):
        self.registry=AgentRegistry()
        self.registry.register_agent(Agent("planner-1","Planner",frozenset({"plan"}),max_concurrency=2))
        self.registry.register_agent(Agent("coder-1","Coder",frozenset({"code"})))
        self.registry.register_group(AgentGroup("core","Core",("planner-1","coder-1")))
        self.scheduler=Scheduler(self.registry,Governor())
    def test_group_routing(self): self.assertEqual(self.registry.route("code","core").id,"coder-1")
    def test_worker_executes(self):
        r=self.scheduler.dispatch(Task("t1","m1","code",{"value":3}),lambda t:{"value":t.input["value"]+1})
        self.assertEqual(r.state,WorkerState.SUCCEEDED); self.assertEqual(r.output["value"],4)
    def test_high_impact_requires_approval(self):
        r=self.scheduler.dispatch(Task("t2","m1","code",{"action":"deploy"}),lambda t:{"ok":True})
        self.assertEqual(r.state,WorkerState.BLOCKED)
    def test_approved_high_impact(self):
        r=self.scheduler.dispatch(Task("t3","m1","code",{"action":"deploy","approved":True}),lambda t:{"ok":True})
        self.assertEqual(r.state,WorkerState.SUCCEEDED)

if __name__=="__main__": unittest.main()
