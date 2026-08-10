# Changelog

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
