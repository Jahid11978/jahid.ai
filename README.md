# JAHID.AI

Unified AI platform monorepo and controlled agent-engineering system.

## Current baseline: v27.5.0

JAHID.AI consolidates the cognitive core, agent runtime, workflows, skills/tools, memory fabric, telemetry, reliability, governance, GitHub controls, and deployment boundaries under one repository.

## Platform layers

- Universal control plane
- Cognitive core and multi-agent orchestration
- Agent runtime and lifecycle governance
- Workflow and task execution
- Skills and tool registry
- Research and knowledge systems
- Unified memory gateway
- Working, episodic, semantic, procedural, project, agent and knowledge memory
- Retrieval, ranking and provenance
- Retention, archive, export and deletion
- Application encryption boundary
- Storage adapter contracts
- Backup and recovery boundaries
- Observability and telemetry
- Structured agent, workflow, memory and security events
- Trace and correlation IDs
- Component health registry
- Autonomous reliability and bounded self-healing
- Failure classification and bounded recovery
- Circuit breakers and verification
- Approved-target rollback coordination
- GitHub engineering controls
- Cloudflare deployment boundary
- Governance, ownership and third-party records

## Autonomous GitHub engineering

The repository now defines an explicit control loop:

```text
Request
  ↓
Inspect
  ↓
Plan
  ↓
Risk classify
  ↓
Create branch
  ↓
Implement
  ↓
Test
  ↓
Security checks
  ↓
Review
  ↓
Draft PR
  ↓
Approval policy
  ↓
Merge
  ↓
Deploy
  ↓
Health verify
  ↓
Rollback / escalate when required
```

See:

- `AGENTS.md` — repository agent operating contract
- `AGENT_GOVERNANCE.md` — agent governance
- `docs/autonomy/control-plane.md` — autonomous GitHub control plane
- `docs/custom-gpt/JAHID_GITHUB_AGENT.md` — Custom GPT instruction set

## Reliability

Recovery is fail-closed:

```text
Detect → Classify → Protect → Recover → Verify → Resume
                                  ↓
                            Rollback / Escalate
```

Missing handlers, missing verification, malformed health results, and unavailable rollback handlers cannot be treated as successful recovery.

## CI

Pull requests and pushes to `main` run the unified Python checks:

```text
Compile sources
    ↓
Backend tests
    ↓
Root tests
    ↓
Repository doctor
```

Additional workflows cover CodeQL, memory-fabric tests, and reliability tests.

## Local validation

From the repository root:

```bash
python -m compileall -q backend tests scripts
python -m unittest discover -s backend/tests -p 'test_*.py' -v
python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/jahid_doctor.py
```

## Safety boundary

Autonomous agents may inspect repositories, create branches, prepare fixes, run tests, and open draft PRs. Production deployment, destructive actions, authentication changes, secret changes, financial actions, ownership/licensing changes, and other high-impact operations remain approval-gated.

JAHID.AI must report evidence for every completed action. It must never invent test results, service health, runtime metrics, deployment state, or recovery success.
