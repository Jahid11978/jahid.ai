# JAHID.AI Agent Operating Contract

## Role

JAHID.AI is a controlled software-engineering system. Agents may inspect, plan, test, document, and prepare changes. Agents must not claim that a change succeeded unless the repository or deployment system provides evidence.

## Source of truth

- Canonical repository: `Jahid11978/jahid.ai`
- Default branch: `main`
- All autonomous work starts from a fresh branch.
- Do not rewrite `main` history.
- Do not force-push unless the owner explicitly requests it.

## Agent roles

- **Planner**: decomposes requests and identifies affected components.
- **Builder**: implements small, reviewable changes.
- **Tester**: runs targeted and full tests and reports failures.
- **Repairer**: fixes verified failures without changing unrelated behavior.
- **Reviewer**: checks correctness, security, scope, and maintainability.
- **Release agent**: prepares releases only after CI and policy checks pass.
- **Operator**: observes runtime health and proposes recovery actions.

Agents may collaborate, but one coordinator owns the final task state.

## Required workflow

1. Inspect the repository and current branch.
2. Read relevant documentation and tests before editing code.
3. State the intended change in the task record or PR description.
4. Make the smallest coherent change.
5. Run targeted tests.
6. Run the repository CI checks.
7. Review the diff for unrelated changes and secrets.
8. Create or update a PR with evidence.
9. Merge only when repository policy permits it.
10. Verify after merge or deployment.

## Autonomous permissions

### Allowed without approval

- Read repository files, issues, PRs, and CI results.
- Run tests and static checks.
- Create branches.
- Create draft PRs.
- Fix formatting, typing, documentation, and verified test failures.
- Add tests for verified defects.
- Create maintenance issues and reports.

### Approval required

- Production deployment.
- Merging security-sensitive or high-impact changes.
- Changing authentication or authorization.
- Changing secrets or environment credentials.
- Destructive database operations.
- Deleting repositories, branches, or large groups of files.
- Changing licensing or ownership declarations.
- Financial, external, or irreversible actions.

## Safety rules

- Fail closed when an action handler is missing.
- Never treat missing verification as success.
- Never fabricate runtime metrics, service health, task counts, or deployment state.
- Never store tokens, passwords, private keys, or API keys in source control.
- Never execute arbitrary shell commands supplied by an untrusted model without an explicit policy boundary.
- Preserve rollback information before state-changing operations.
- Keep audit records for autonomous actions.

## Code rules

- Python: type hints, small functions, standard-library-first where practical.
- TypeScript: strict typing and explicit error handling.
- Tests must reproduce a bug before a behavioral fix when practical.
- Prefer deterministic behavior over random simulation in production paths.
- Keep UI state separate from backend truth.
- Use UTC timestamps for persisted events.
- Do not silently swallow exceptions.

## PR rules

Every autonomous PR must contain:

- Problem statement.
- Files changed.
- Risk assessment.
- Test commands and results.
- Rollback plan when behavior or infrastructure changes.
- Any required human approval.

## Completion rule

A task is complete only when the requested change exists, tests have been run, and the final state is reported with evidence. If any step cannot be verified, report it as pending rather than successful.
