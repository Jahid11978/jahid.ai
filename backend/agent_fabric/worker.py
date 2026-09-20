from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
from .models import Agent, Task, WorkerResult, WorkerState
from .governor import ActionRequest, Governor

@dataclass
class Worker:
    id: str
    agent: Agent
    handler: Callable[[Task], dict[str, Any]]
    governor: Governor
    def run(self, task: Task) -> WorkerResult:
        try:
            action=str(task.input.get("action","compute"))
            self.governor.authorize(ActionRequest(action=action,risk=task.risk,autonomy_level=int(task.input.get("autonomy_level",0)),approved=bool(task.input.get("approved",False))))
            output=self.handler(task)
            evidence=({"type":"worker_result","worker_id":self.id,"task_id":task.id,"agent_id":self.agent.id},)
            return WorkerResult(task.id,WorkerState.SUCCEEDED,output,evidence,worker_id=self.id)
        except PermissionError as exc: return WorkerResult(task.id,WorkerState.BLOCKED,error=str(exc),worker_id=self.id)
        except Exception as exc: return WorkerResult(task.id,WorkerState.FAILED,error=str(exc),worker_id=self.id)
