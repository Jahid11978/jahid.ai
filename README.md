# JAHID.AI

Unified AI platform monorepo.

## Current baseline: v27.3 — Observability & Telemetry Fabric

JAHID.AI consolidates the cognitive core, agent runtime, workflows, skills/tools, operations, security, deployment, GitHub controls, v26.0 Unified Data & Memory Fabric, and v27.3 operational telemetry under one repository governance layer.

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
- Voice and vision systems
- Authentication and access control
- REST, GraphQL and WebSocket APIs
- Docker/Kubernetes and Cloudflare deployment layers
- GitHub Actions CI/CD
- Governance, ownership and third-party license records

## Observability boundary

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
      Universal Control Plane
```

Telemetry is observational. It does not grant permissions, approve actions, or bypass security and human-approval controls. Sensitive fields are redacted before export.

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

The memory package lives under `backend/memory/`. The telemetry package lives under `backend/telemetry/`. Local adapters remain deterministic for tests/development. Production storage and telemetry exporters should be injected behind their respective boundaries.

Run the repository tests from the project root with:

```bash
python -m unittest discover -s backend/tests
```
