# JAHID.AI Repository Map

## Canonical repository

`Jahid11978/jahid.ai` is the canonical JAHID.AI source of truth.

## Embedded reference material

The `repos/` directory contains small reference manifests and imported snapshots. These are references, not independent production runtimes.

## Related repositories

Several GitHub repositories contain JARVIS, OpenClaw, frontend, and experiment code. They should be treated as source material or integration candidates until their code is deliberately migrated into the canonical architecture.

Examples include:

- `Jahid11978/ai-jarvis-system`
- `Jahid11978/crispy-system.`
- `Jahid11978/openclaw-jahid.ai`
- `Jahid11978/openclaw-Jahid`
- `mdjahid11978-design/JARVIS-1`
- `mdjahid11978-design/ai-jarvis-system-93b01524`
- `mdjahid11978-design/jahid-nextjs`

## Consolidation rule

Do not copy a complete repository into the canonical repository merely to make it look complete. First classify the source as:

1. production component
2. reusable library
3. integration adapter
4. reference implementation
5. obsolete prototype

Then migrate only the required code with provenance and tests.

## Recommended target structure

```text
jahid.ai/
├── apps/              # user-facing and service applications
├── backend/           # Python control-plane components
├── reliability/       # recovery and verification boundaries
├── memory/            # memory fabric contracts and adapters
├── integrations/      # external systems such as GitHub/OpenClaw
├── infra/             # deployment definitions
├── docs/              # architecture and operating documentation
├── scripts/           # deterministic maintenance tooling
├── tests/             # cross-component tests
└── .github/           # CI, security and automation
```

The current repository can move toward this structure incrementally. Avoid a large destructive reorganization while the system is still changing rapidly.
