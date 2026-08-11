# JAHID.AI

Unified AI platform monorepo.

## Current baseline: v27.9.0 — Full Release Control Plane

JAHID.AI now combines the cognitive core, agent runtime, workflows, Unified Data & Memory Fabric, reliability fabric, security controls, Cloudflare deployment layer, and a release control plane for immutable multi-environment promotion.

### v27.9 release control

- Build once; promote the same immutable artifact digest.
- Dependency-aware release graph.
- Environment-specific policy gates.
- Schema compatibility and migration safety.
- Contract-test admission.
- SBOM, provenance, signature, secret and vulnerability evidence.
- Cloudflare Worker Version promotion without rebuilding between environments.
- Cloudflare gradual deployment support using the current one/two-version model.
- Canary SLO comparison and minimum-sample gates.
- Automatic LKG composition tracking.
- Component-specific rollback strategies.
- Runtime desired/observed-state reconciliation.
- Security freeze and quarantine states.
- Hash-linked audit ledger and signed-checkpoint architecture.
- Controller recovery from persisted release state.
- Cloudflare Zone Activation Check as a separate pending-zone readiness operation.

### Operational flow

```text
Build → Sign → SBOM → Provenance → Security Admission
  → Schema Compatibility → Contract Tests → Staging
  → Canary → SLO → Production → Runtime Verification → LKG
```

### Cloudflare

Worker promotion uses existing Worker Version IDs through the Workers deployment API. The controller does not rebuild the Worker when moving from staging to canary or production.

A pending zone activation check is separate from Worker deployment and uses the Cloudflare Zone Activation Check API when `CLOUDFLARE_PENDING_ZONE_ID` is explicitly configured.

Required production secrets:

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

Optional production variable:

- `CLOUDFLARE_PENDING_ZONE_ID`

### Local validation

```bash
python -m compileall -q backend
python -m unittest discover -s backend/tests -v
python scripts/release/promote.py releases/manifests/v27.9.0.json --environment staging --evidence releases/evidence/admission.json
```

### Existing platform layers

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

Telemetry is observational. It does not grant permissions, approve actions, or bypass security and human-approval controls. Sensitive fields are redacted before export.

Reliability and release recovery are bounded and deny-by-default. High-impact recovery requires the configured control-plane approval boundary. The system does not invent rollback revisions, bypass authentication, delete data, or perform unapproved external or financial actions.
