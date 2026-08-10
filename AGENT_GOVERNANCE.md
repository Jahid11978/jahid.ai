# JAHID.AI Agent Governance

Agents operate under JAHID.AI policy and authorized human control.

Every production agent must have an agent ID, version, purpose, controller, permission profile, tool profile, data-access profile, risk classification, audit identity, and lifecycle state.

Lifecycle: DRAFT → TESTING → SECURITY REVIEW → APPROVED → ACTIVE → SUSPENDED → RETIRED.

Agents must not grant themselves permissions, bypass security controls, alter ownership records, access credentials outside policy, or perform restricted actions without the required approval.

Agent actions covered by the audit policy must record technical provenance including agent, workflow, task, model, tool, commit and timestamp where available.