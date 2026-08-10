# JAHID.AI

Unified AI platform monorepo.

## Current baseline: v27.4 — Autonomous Reliability & Self-Healing Fabric

JAHID.AI consolidates the cognitive core, agent runtime, workflows, skills/tools, operations, security, deployment, GitHub controls, v26.0 Unified Data & Memory Fabric, v27.3 operational telemetry, and v27.4 bounded reliability under one repository governance layer.

### Platform layers

- Universal Control Plane
- Cognitive Core and multi-agent orchestration
- Agent runtime and lifecycle governance
- Workflow engine
- Skills and tool registry
- Research and knowledge systems
- Unified Memory Gateway
- Working, episodic, semantic, procedural, project, agent and knowledge memory
- Retrieval, ranking and provenance
- Retention, archive, export and deletion
- AES-256-GCM application encryption boundary
- PostgreSQL, Redis and vector-store adapter contracts
- Backup registry, checksum verification and disaster recovery
- Observability and telemetry fabric
- Structured agent, workflow, memory and security events
- Trace and correlation IDs
- Metrics and component health
- Credential redaction at telemetry boundaries
- Autonomous Reliability & Self-Healing Fabric
- Failure classification and bounded recovery
- Circuit breakers and recovery verification
- Approved-target rollback coordination
- Escalation for unsafe or non-retryable failures
- Voice and vision systems
- Authentication and access control
- REST, GraphQL and WebSocket APIs
- Docker/Kubernetes and Cloudflare deployment layers
- GitHub Actions CI/CD
- Governance, ownership and third-party license records

## Unified operational flow

```text
Agent / Workflow / Memory / Security
                |
        Telemetry Boundary
                |
     +----------+----------+
     |          |          |
   Events     Metrics    Traces
     |          |          |
     +----------+----------+
                |
        Health Registry
                |
      Reliability Engine
                |
 Detect → Classify → Protect
                |
             Recover
                |
             Verify
          /           \
       healthy       failed
          |             |
        Resume    Rollback / Escalate
          |             |
          +------ Control Plane
```

Telemetry is observational. It does not grant permissions, approve actions, or bypass security and human-approval controls. Sensitive fields are redacted before export.

Reliability is bounded and deny-by-default. High-impact recovery requires an explicit control-plane approval token. The reliability layer cannot invent rollback revisions, bypass authentication, delete data, or perform unapproved external or financial actions.

## Memory architecture

```text
Agent / Workflow
      |
Memory Gateway
      |
Permission Check
      |
Memory Policy
      |
Retrieve / Write
      |
Provenance
      |
+-------------------------------+
| PostgreSQL | Redis | Vector DB |
+-------------------------------+
      |
Backup / Recovery / Lifecycle
```

## Development

The memory package lives under `backend/memory/`. The telemetry package lives under `backend/telemetry/`. The reliability package lives under `backend/reliability/`. Local adapters remain deterministic for tests/development. Production storage, telemetry exporters, and infrastructure recovery handlers should be injected behind their respective boundaries.

Run the repository tests from the project root with:

```bash
python -m unittest discover -s backend/tests
```
