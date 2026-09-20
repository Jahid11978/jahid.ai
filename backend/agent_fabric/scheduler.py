from __future__ import annotations
from collections import defaultdict
from typing import Callable, Any
from .models import Mission, Task, WorkerResult, WorkerState
from .registry import AgentRegistry
from .worker import Worker
from .governor import Governor

class Scheduler:
    def __init__(self,registry: AgentRegistry,governor: Governor|None=None):
        self.registry=registry; self.governor=governor or Governor(); self.results={}; self._active=defaultdict(int)
    def dispatch(self,task: Task,handler: Callable[[Task],dict[str,Any]],group_id=None):
        agent=self.registry.route(task.capability,group_id)
        if self._active[agent.id]>=agent.max_concurrency: return WorkerResult(task.id,WorkerState.BLOCKED,error="agent concurrency limit reached")
        self._active[agent.id]+=1
        try:
            result=Worker("worker-"+task.id,agent,handler,self.governor); result=result.run(task); self.results[task.id]=result; return result
        finally: self._active[agent.id]-=1
    def run_mission(self,mission: Mission,handlers: dict[str,Callable],group_id=None):
        results=[]
        for task in mission.tasks:
            handler=handlers.get(task.capability)
            result=self.dispatch(task,handler,group_id) if handler else WorkerResult(task.id,WorkerState.FAILED,error=f"no handler for capability: {task.capability}")
            results.append(result)
            if result.state in {WorkerState.BLOCKED,WorkerState.FAILED}: break
        return tuple(results)
