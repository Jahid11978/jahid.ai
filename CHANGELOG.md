# Changelog

## v27.5.0 — 2026-08-10

### Added
- Unified JAHID.AI agent operating contract in `AGENTS.md`.
- Autonomous GitHub control-plane architecture and risk model.
- Custom GPT configuration for the JAHID.AI GitHub Chief Engineer.
- Deterministic repository doctor for CI health checks.
- Unified Python CI workflow for compilation, backend tests, root tests, and repository checks.

### Fixed
- Reliability recovery now fails closed when required handlers are missing.
- Missing protection, recovery, verification, rollback, and resume handlers no longer count as successful execution.
- Recovery verification remains fail-closed for missing or malformed health results.
- Reliability tests now cover missing handlers and unhealthy verification rollback.

### Safety
- Autonomous operations are branch-first and evidence-driven.
- High-impact, destructive, security-sensitive, financial, ownership, licensing, and production actions remain approval-gated.
- Agents must not fabricate metrics, test results, deployment status, or successful recovery.

### Baseline
- Repository `VERSION` updated to `27.5.0`.

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

### Safety
- High-impact recovery requires an explicit control-plane approval token.
- Recovery cannot invent rollback revisions, bypass security, delete data, or approve external/financial actions.
- Missing or malformed health verification now escalates instead of resuming unverified operation.

### Baseline alignment
- Repository `VERSION` updated to `27.4.0`.
- README updated to the v27.4 platform baseline.
