# JAHID.AI

Unified AI platform monorepo for governed agents, workers, memory, control, reliability and release operations.

## Platform layers

- Agent Fabric: agent registry, groups, capability routing, workers and scheduler.
- Control Plane: policy-gated missions, approvals and release orchestration.
- Memory Fabric: working, episodic, semantic, procedural, project, agent and knowledge memory.
- Reliability Fabric: health, bounded recovery, rollback contracts and verification.
- Release Control: immutable artifact promotion, evidence admission, canary policy and LKG tracking.
- Security boundary: deny-by-default governance for high-impact actions.
- Cloudflare layer: Worker deployment and promotion without rebuilding between environments.

## Agent execution flow

Request -> Mission -> Task -> Agent Group -> Worker -> Governance -> Registered Adapter -> Evidence -> Verification -> Audit -> Memory

Workers do not receive arbitrary command execution. High-impact actions require explicit approval and registered execution adapters.

## Local validation

    python -m compileall -q backend
    python -m unittest discover -s backend/tests -v
    python -m unittest discover -s tests -v
    python scripts/jahids.py agent-demo

See docs/architecture/AGENT_FABRIC.md and docs/architecture/PLATFORM_UNIFIED.md for the platform contracts.

Built by Jahid.
