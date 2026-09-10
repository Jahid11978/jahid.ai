# JAHID.AI Autonomous GitHub Control Plane

## Objective

Provide a controlled software-engineering loop that can inspect the repository, diagnose failures, prepare fixes, validate them, and report evidence.

## Control loop

```text
Request
  -> Coordinator
  -> Repository inspection
  -> Plan
  -> Risk classification
  -> Branch
  -> Implement
  -> Test
  -> Security checks
  -> Review
  -> Draft PR
  -> Approval policy
  -> Merge
  -> Deployment
  -> Health verification
  -> Rollback or close
```

## Agent contract

| Agent | Responsibility | Default permission |
| --- | --- | --- |
| Coordinator | owns task state | read + planning |
| Planner | decomposition | read |
| Builder | code changes | branch write |
| Tester | tests and diagnostics | read + execute |
| Repairer | verified fixes | branch write |
| Reviewer | risk and diff review | read |
| Release | release preparation | approval-gated |
| Operator | runtime health | read + recovery proposal |

## Risk classes

- **LOW**: documentation, formatting, tests, deterministic refactors. Can proceed automatically.
- **MEDIUM**: dependency updates, API behavior changes, non-destructive infrastructure changes. Draft PR and CI required.
- **HIGH**: authentication, security controls, production infrastructure, data migrations. Human approval required.
- **CRITICAL**: destructive, financial, ownership, secret, or irreversible operations. Human approval required and the agent must stop until approval exists.

## Evidence requirements

Every autonomous task records:

- repository and commit SHA
- branch name
- task identifier
- files changed
- tests executed
- test results
- security results
- approval state
- deployment result, if applicable
- rollback target, when applicable

## GitHub behavior

The GitHub agent may automatically:

- inspect code, issues, PRs, and workflow results
- create branches
- create draft PRs
- add tests
- repair verified CI failures
- update documentation
- create maintenance issues

The GitHub agent must not automatically:

- expose secrets
- change repository ownership
- change licensing
- delete repositories
- bypass branch protection
- merge high-impact changes without policy approval
- report an unverified action as successful

## Recovery

Recovery is fail-closed. Missing handlers, missing verification, malformed health results, and unavailable rollback targets lead to escalation rather than an assumed success state.
