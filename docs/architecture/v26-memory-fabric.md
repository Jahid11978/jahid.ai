# JAHID.AI v26.0 — Unified Data & Memory Fabric

## Boundary

Agents and workflows access memory only through `MemoryGateway`.

```text
Agent / Workflow
      |
Memory Gateway
      |
Permission Check -> Memory Policy
      |
Retrieve / Write
      |
Provenance
      |
PostgreSQL | Redis | Vector Store
      |
Backup / Recovery / Lifecycle
```

## Memory classes

- `working`: current task context
- `episodic`: events and workflow history
- `semantic`: facts and concepts
- `procedural`: approved procedures
- `project`: project-scoped context
- `agent`: agent operational context
- `knowledge`: validated research and documentation
- `archive`: historical records

Memory classification is explicit so temporary context does not become permanent memory by default.

## Record metadata

Every `MemoryRecord` contains an ID, type, source, timestamps, actor, scope, confidence, classification and retention policy. Agent and project identifiers are optional metadata.

## Retrieval

The gateway enforces access before retrieval. The retrieval pipeline then applies type filtering and deterministic ranking. Production vector retrieval can be connected through `VectorMemoryStore` without exposing the vector database to agents.

## Lifecycle

```text
CREATE -> CLASSIFY -> STORE -> USE -> REFRESH -> ARCHIVE -> DELETE
```

Retention defaults live in `retention.py` and can be replaced by a policy service.

## User control

`export.py` serializes memory records. `deletion.py` and the gateway provide the forget boundary. A production delete implementation must propagate the operation to durable storage, vector indexes, caches and replicas according to policy.

## Security

`encryption.py` provides AES-256-GCM. The key is supplied at runtime and is not stored in the repository or included in prompts. Production key material belongs in a secret manager/KMS.

## Backup and recovery

`backup.py` registers artifacts with SHA-256 checksums and marks them verified only after a payload verification operation. `recovery.py` defines the recovery order:

1. Detect
2. Classify
3. Protect current state
4. Restore service
5. Restore database
6. Restore memory indexes
7. Verify
8. Resume

A backup is therefore not considered recoverable until restoration verification succeeds.

## Production adapters

`storage.py` defines contracts for PostgreSQL, Redis session state and vector memory. The repository currently ships a deterministic in-memory adapter for development/tests. Production adapters must be injected into `MemoryGateway`.

## Next baseline

v26.1 can connect OpenTelemetry, logs, metrics, traces, agent events, workflow execution, infrastructure health, GitHub Actions and usage/cost telemetry to the Universal Control Plane.
