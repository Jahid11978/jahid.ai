# JAHID.AI

Unified AI platform monorepo.

## Current baseline: v26.0 — Unified Data & Memory Fabric

JAHID.AI now provides a single memory boundary for agents, workflows and cognitive services. Agents do not access PostgreSQL, Redis or vector storage directly; they use the Memory Gateway.

### Platform modules

- Next.js web application
- FastAPI backend
- AI kernel and multi-agent orchestration
- Unified Memory Gateway
- Working, episodic, semantic, procedural, project, agent and knowledge memory
- Retrieval, ranking and provenance
- Retention, archive, export and deletion
- Authenticated encryption boundary
- PostgreSQL, Redis and vector-store adapter contracts
- Backup registry, checksum verification and disaster-recovery plan
- Voice and vision systems
- Workflow engine
- Agent marketplace and extension framework
- SDKs and CLI
- Authentication and billing
- REST, GraphQL and WebSocket APIs
- Docker and Kubernetes deployment
- GitHub Actions CI/CD
- Monitoring and logging
- Documentation and automated tests

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

Every record carries provenance metadata including source, timestamps, actor, scope, confidence, classification and retention policy.

## Security boundary

Sensitive memory uses an application encryption boundary backed by AES-256-GCM. Production keys must come from an external secret manager and never enter agent prompts.

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
```
