# JAHIDS.AI Agent Fabric

The repository now includes a governed multi-agent contract for agents, groups, workers and scheduling.

## Flow

Request -> Mission -> Task -> Registry -> Group/Agent Route -> Worker -> Governor -> Registered Handler -> Evidence -> Result

## Agent groups

A group is a routing boundary containing registered agents. Agents advertise capabilities and a concurrency limit.

## Workers

Workers execute registered handlers only. Each task passes through the Governor before its handler runs. High-impact actions such as deployment, credential changes, financial actions, destructive operations and ownership changes require explicit approval.

## Scheduler

The scheduler routes tasks by capability, applies per-agent concurrency limits and stores results. A distributed queue can implement the same interface later without changing mission or task contracts.

## Autonomy

Autonomy levels 0-5 describe the requested operating level. They do not grant blanket permission. Governance evaluates the requested action separately.

No arbitrary shell execution or direct external side effects are part of this worker contract.
