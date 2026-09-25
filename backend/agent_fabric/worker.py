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
        """Authorize and run a task, returning execution evidence on success.

        Convert ``PermissionError`` to a blocked result and other ``Exception``
        instances to failed results instead of propagating them.
        """
        try:
            approval=task.approval
            approved=(approval is not None and approval.approved is True and approval.task_id == task.id and approval.action == task.action and approval.actor == task.actor)
            if task.requires_approval and not approved:
                raise PermissionError(f"approval required for action: {task.action}")
            self.governor.authorize(ActionRequest(action=task.action,risk=task.risk,autonomy_level=task.autonomy_level,approved=approved,actor=task.actor))
            output=self.handler(task)
            evidence=({"type":"worker_result","worker_id":self.id,"task_id":task.id,"agent_id":self.agent.id},)
            return WorkerResult(task.id,WorkerState.SUCCEEDED,output,evidence,worker_id=self.id)
        except PermissionError as exc: return WorkerResult(task.id,WorkerState.BLOCKED,error=str(exc),worker_id=self.id)
        except Exception as exc: return WorkerResult(task.id,WorkerState.FAILED,error=str(exc),worker_id=self.id)
