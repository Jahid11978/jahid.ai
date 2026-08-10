# JAHID.AI

Unified AI platform monorepo.

## Current baseline: v27.4.1 — Reliability, Full Validation & Production Deployment

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
- Full repository validation workflow
- Cloudflare Worker configuration validation
- Cloudflare production deployment workflow
- Deployment URL smoke testing
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

## Full validation

Every push to `main` and every pull request targeting `main` runs the full validation workflow:

```text
Compile backend
      ↓
Full backend test discovery
      ↓
Reliability test suite
      ↓
Cloudflare Worker dry-run validation
```

The workflow also supports `workflow_dispatch` for an explicit manual validation run.

## Production deployment

Every push to `main` triggers the Cloudflare production deployment workflow. It:

1. Authenticates using GitHub repository/environment secrets.
2. Deploys the Worker with Wrangler.
3. Requires a deployment URL.
4. Performs an HTTP smoke test against the deployed URL.
5. Fails the workflow if deployment or verification fails.

Required GitHub production environment secrets:

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

Cloudflare's official documentation requires a Cloudflare API token and account ID for non-interactive GitHub Actions deployment. citeturn0search0

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

Run the complete local validation from the project root with:

```bash
python -m compileall -q backend
python -m unittest discover -s backend/tests -v
python -m unittest backend.tests.test_reliability -v
```
