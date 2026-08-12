-- JAHID.AI production control plane schema.
-- Apply with your existing PostgreSQL migration runner.

CREATE TABLE IF NOT EXISTS controller_leases (
    controller_name TEXT PRIMARY KEY,
    holder_id TEXT NOT NULL,
    epoch BIGINT NOT NULL DEFAULT 1,
    lease_until TIMESTAMPTZ NOT NULL,
    heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS deployment_locks (
    environment TEXT PRIMARY KEY,
    locked BOOLEAN NOT NULL DEFAULT FALSE,
    reason TEXT,
    locked_by TEXT,
    locked_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS deployment_desired_state (
    environment TEXT PRIMARY KEY,
    artifact_id UUID,
    cloudflare_version_id TEXT NOT NULL,
    target_percentage INTEGER NOT NULL DEFAULT 100 CHECK (target_percentage BETWEEN 0 AND 100),
    generation BIGINT NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active',
    updated_by TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS deployment_observed_state (
    environment TEXT PRIMARY KEY,
    cloudflare_deployment_id TEXT,
    cloudflare_version_id TEXT,
    traffic JSONB NOT NULL DEFAULT '{}'::jsonb,
    observation_status TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS deployment_drift (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment TEXT NOT NULL,
    desired_generation BIGINT NOT NULL,
    desired_version_id TEXT,
    observed_version_id TEXT,
    drift_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS deployment_incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment TEXT NOT NULL,
    rollout_id UUID,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    reason TEXT NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS release_event_chain (
    sequence BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    environment TEXT,
    artifact_id UUID,
    cloudflare_version_id TEXT,
    actor TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    previous_hash TEXT,
    event_hash TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS release_provenance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID,
    repository TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    github_run_id BIGINT NOT NULL,
    github_workflow TEXT NOT NULL,
    artifact_digest TEXT NOT NULL,
    sbom_digest TEXT,
    provenance_digest TEXT,
    cloudflare_version_id TEXT,
    source_verified BOOLEAN NOT NULL DEFAULT FALSE,
    artifact_verified BOOLEAN NOT NULL DEFAULT FALSE,
    provenance_verified BOOLEAN NOT NULL DEFAULT FALSE,
    sbom_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(repository, commit_sha, github_run_id)
);

CREATE TABLE IF NOT EXISTS release_signatures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID,
    artifact_digest TEXT NOT NULL,
    signature_type TEXT NOT NULL,
    signer_identity TEXT,
    issuer TEXT,
    bundle_digest TEXT,
    signature_verified BOOLEAN NOT NULL DEFAULT FALSE,
    transparency_verified BOOLEAN NOT NULL DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    verifier TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS deployment_receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment TEXT NOT NULL,
    artifact_id UUID,
    artifact_digest TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    cloudflare_version_id TEXT NOT NULL,
    deployment_id TEXT,
    rollout_id UUID,
    event_sequence BIGINT,
    receipt_digest TEXT NOT NULL,
    signature_bundle JSONB,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS recovery_checkpoints (
    environment TEXT PRIMARY KEY,
    rollout_id UUID,
    desired_generation BIGINT NOT NULL,
    last_event_sequence BIGINT,
    last_verified_cloudflare_version TEXT,
    last_verified_artifact_digest TEXT,
    checkpoint_hash TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS recovery_incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment TEXT,
    incident_type TEXT NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'open',
    details JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_release_event_chain_env ON release_event_chain(environment, sequence);
CREATE INDEX IF NOT EXISTS idx_deployment_drift_env ON deployment_drift(environment, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_deployment_receipts_env ON deployment_receipts(environment, created_at DESC);
