# JAHID.AI

Unified AI platform monorepo.

## Current baseline: v27.2 — Unified Platform + Governance

JAHID.AI consolidates the existing cognitive core, agent runtime, workflows, skills/tools, operations, security, deployment, GitHub controls and the v26.0 Unified Data & Memory Fabric under one repository governance layer.

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
- Voice and vision systems
- Authentication and access control
- REST, GraphQL and WebSocket APIs
- Docker/Kubernetes and Cloudflare deployment layers
- GitHub Actions CI/CD
- Monitoring and logging
- Governance, ownership and third-party license records

## Governance

The repository's governance layer records ownership intent for original JAHID.AI material while preserving third-party rights. See `OWNERSHIP.md`, `GOVERNANCE.md`, `AGENT_GOVERNANCE.md`, `PROVENANCE.md`, `THIRD_PARTY.md` and `REGISTRATION.md`.

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

## Memory types

`working` · `episodic` · `semantic` · `procedural` · `project` · `agent` · `knowledge` · `archive`

## Security boundary

Sensitive memory uses an application encryption boundary. Production keys must come from an external secret manager and must never enter agent prompts.

## Development

The memory package lives under `backend/memory/`. The local adapter is deterministic and intended for tests/development. PostgreSQL, Redis and vector storage are represented by explicit adapter contracts so production implementations can be connected without allowing agents to bypass the gateway.

Install the memory dependency set with:

```bash
python -m pip install -r backend/requirements-memory.txt
```

Run the memory tests from `backend/`:

```bash
python -m unittest discover -s tests
```

## Architecture

```text
User Apps
   |
Universal Control Plane
   |
FastAPI Gateway
   |
Cognitive Core + Agent Runtime
   |
Skills + Tools + Workflows
   |
Memory Gateway
   |
PostgreSQL + Redis + Vector Store
   |
Governance + Provenance + Audit
```

## Rights

JAHID.AI is proprietary by default unless a specific file or component states otherwise. Third-party components remain subject to their respective licenses and terms. See `THIRD_PARTY.md` and `LICENSE_REGISTRY.md` when present.