# JAHID.AI Release Control Plane v27.9

## Guarantees

- Build once; promote the same artifact digest through environments.
- Release dependencies form a directed acyclic graph.
- Database migrations use compatibility gates and forward-fix rollback when required.
- Security evidence is required before admission.
- Cloudflare Worker promotion operates on existing Worker Version IDs; it does not rebuild the artifact during promotion.
- Cloudflare gradual deployments are limited to the currently supported one- or two-version model.
- Canary decisions compare stable and canary SLOs and require a minimum sample.
- LKG is a complete release composition, including database schema and Worker version.
- Runtime drift can freeze a release instead of silently overwriting unexpected state.
- Audit events form a hash chain and can be checkpointed independently.

## Cloudflare

The Cloudflare adapter separates zone activation checks from Worker deployments. A pending zone activation check calls `PUT /zones/{zone_id}/activation_check`. Worker traffic promotion uses the Workers deployments API and existing version IDs.

Required secrets for production:

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

Optional production variable:

- `CLOUDFLARE_PENDING_ZONE_ID`

The optional zone variable is used only when a pending zone requires an explicit activation check.

## Release sequence

```text
Build → Sign → SBOM → Provenance → Security Admission
  → Schema Compatibility → Contract Tests → Staging
  → Canary → SLO → Production → Runtime Verification → LKG
```

## Rollback

Rollback is component-specific. Cloudflare Workers can promote the registered LKG Worker Version to 100% traffic. Database migrations marked forward-only are not automatically reversed.

## Local validation

```bash
python -m compileall -q backend
python -m unittest discover -s backend/tests -v
python scripts/release/promote.py releases/manifests/v27.9.0.json --environment staging --evidence releases/evidence/admission.json
```
