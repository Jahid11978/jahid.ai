from __future__ import annotations
from collections import defaultdict
from threading import Lock
from typing import Callable, Any
from .models import Mission, Task, WorkerResult, WorkerState
from .registry import AgentRegistry
from .worker import Worker
from .governor import Governor

class Scheduler:
    def __init__(self,registry: AgentRegistry,governor: Governor|None=None):
        """Initialize a scheduler for a registry and optional governor."""
        self.registry=registry; self.governor=governor or Governor(); self.results={}; self._active=defaultdict(int); self._lock=Lock()
    def _record_result(self,result: WorkerResult):
        with self._lock: self.results[result.task_id]=result
        return result
    def dispatch(self,task: Task,handler: Callable[[Task],dict[str,Any]],group_id=None):
        """Route and run a task while enforcing the agent's concurrency limit.

        Return a blocked result without invoking the handler when the selected
        agent is at capacity. Routing errors propagate; worker execution errors
        are returned as blocked or failed results.
        """
        agent=self.registry.route(task.capability,group_id)
        with self._lock:
            if self._active[agent.id]>=agent.max_concurrency:
                blocked=WorkerResult(task.id,WorkerState.BLOCKED,error="agent concurrency limit reached")
            else:
                self._active[agent.id]+=1; blocked=None
        if blocked is not None: return self._record_result(blocked)
        try:
            result=Worker("worker-"+task.id,agent,handler,self.governor); result=result.run(task); return self._record_result(result)
        finally:
            with self._lock: self._active[agent.id]-=1
    def run_mission(self,mission: Mission,handlers: dict[str,Callable],group_id=None):
        """Run mission tasks in order until one is blocked or fails.

        A task without a capability handler produces a failed result. Return
        the results collected before and including the first unsuccessful task.
        """
        results=[]
        for task in mission.tasks:
            handler=handlers.get(task.capability)
            result=self.dispatch(task,handler,group_id) if handler else self._record_result(WorkerResult(task.id,WorkerState.FAILED,error=f"no handler for capability: {task.capability}"))
            results.append(result)
            if result.state in {WorkerState.BLOCKED,WorkerState.FAILED}: break
        return tuple(results)
