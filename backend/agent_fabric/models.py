from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

class WorkerState(str, Enum):
    IDLE="idle"; RUNNING="running"; SUCCEEDED="succeeded"; FAILED="failed"; BLOCKED="blocked"

@dataclass(frozen=True)
class Agent:
    id: str
    name: str
    capabilities: frozenset[str] = frozenset()
    group_id: str | None = None
    max_concurrency: int = 1
    enabled: bool = True

@dataclass(frozen=True)
class AgentGroup:
    id: str
    name: str
    agent_ids: tuple[str, ...] = ()
    policy: str = "default"
    enabled: bool = True

@dataclass(frozen=True)
class ApprovalDecision:
    task_id: str
    action: str
    actor: str
    approved: bool

@dataclass(frozen=True)
class Task:
    id: str
    mission_id: str
    capability: str
    input: Mapping[str, Any] = field(default_factory=dict)
    risk: str = "low"
    requires_approval: bool = False
    action: str = "compute"
    actor: str = "system"
    autonomy_level: int = 0
    approval: ApprovalDecision | None = None

@dataclass(frozen=True)
class Mission:
    id: str
    goal: str
    tasks: tuple[Task, ...] = ()
    autonomy_level: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class WorkerResult:
    task_id: str
    state: WorkerState
    output: Mapping[str, Any] = field(default_factory=dict)
    evidence: tuple[Mapping[str, Any], ...] = ()
    error: str | None = None
    worker_id: str | None = None
