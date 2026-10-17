# Changelog

## v27.5.0 — 2026-08-10

### Added
- Unified JAHID.AI agent operating contract in `AGENTS.md`.
- Autonomous GitHub control-plane architecture and risk model.
- Custom GPT configuration for the JAHID.AI GitHub Chief Engineer.
- Deterministic repository doctor for CI health checks.
- Unified Python CI workflow for compilation, backend tests, root tests, and repository checks.
- Multi-environment promotion controller with immutable artifact promotion.
- Environment-specific rollout policy with production human approval.
- Last-known-good and desired-state control-plane schema.
- Continuous reconciliation and safe drift classification.
- Controller leases, epochs, recovery checkpoints, and stale-controller fencing.
- Tamper-evident release event hash chain.
- Release provenance, signature, SBOM, and deployment receipt records.
- Cloudflare API adapter with bounded retry/backoff.
- Cloudflare zone activation-check integration for pending zones.
- GitHub Actions build-once promotion pipeline with artifact attestation.
- Controller recovery verification workflow and safety tests.

### Fixed
- Reliability recovery now fails closed when required handlers are missing.
- Missing protection, recovery, verification, rollback, and resume handlers no longer count as successful execution.
- Recovery verification remains fail-closed for missing or malformed health results.
- Reliability tests now cover missing handlers and unhealthy verification rollback.

### Safety
- Autonomous operations are branch-first and evidence-driven.
- High-impact, destructive, security-sensitive, financial, ownership, licensing, and production actions remain approval-gated.
- Agents must not fabricate metrics, test results, deployment status, or successful recovery.
- Production drift is fail-closed and cannot be auto-repaired.
- Promotion never rebuilds an artifact between environments.
- Unverified provenance, signatures, or SBOM evidence blocks production promotion.
- Unknown Cloudflare state does not trigger an automatic rollback or deployment.
- Stale controllers are fenced by lease epochs.
- Registry/event-chain mismatches create a review condition instead of silently repairing evidence.

### Baseline alignment
- Repository `VERSION` updated to `27.5.0`.
- Production workflow now routes deployment decisions through the JAHID.AI promotion controller.

## v27.4.0 — 2026-08-10

### Added
- Autonomous Reliability & Self-Healing Fabric.
- Failure classification and bounded recovery plans.
- Deny-by-default recovery policy.
- Bounded retries with exponential backoff.
- Component health registry.
- Circuit breaker support.
- Approved-target rollback coordination.
- Recovery verification and escalation.
- Reliability safety and recovery test coverage.
