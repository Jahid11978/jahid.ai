CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS release_registry (
    release_id TEXT PRIMARY KEY,
    artifact_digest TEXT NOT NULL,
    source_commit TEXT NOT NULL,
    sbom_digest TEXT NOT NULL,
    provenance_digest TEXT NOT NULL,
    signature_digest TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'registered',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS release_components (
    release_id TEXT NOT NULL REFERENCES release_registry(release_id),
    component_name TEXT NOT NULL,
    component_kind TEXT NOT NULL,
    artifact_digest TEXT,
    version_id TEXT,
    rollback_strategy TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    PRIMARY KEY (release_id, component_name)
);

CREATE TABLE IF NOT EXISTS release_dependencies (
    release_id TEXT NOT NULL REFERENCES release_registry(release_id),
    component_name TEXT NOT NULL,
    depends_on TEXT NOT NULL,
    PRIMARY KEY (release_id, component_name, depends_on),
    FOREIGN KEY (release_id, component_name)
        REFERENCES release_components(release_id, component_name),
    FOREIGN KEY (release_id, depends_on)
        REFERENCES release_components(release_id, component_name)
);

CREATE TABLE IF NOT EXISTS lkg_registry (
    release_id TEXT PRIMARY KEY,
    state JSONB NOT NULL,
    verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS promotion_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    release_id TEXT NOT NULL REFERENCES release_registry(release_id),
    source_environment TEXT NOT NULL,
    target_environment TEXT NOT NULL,
    artifact_digest TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    promoted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS release_events (
    sequence BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    release_id TEXT,
    environment TEXT,
    component TEXT,
    event_type TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT,
    artifact_digest TEXT,
    version_id TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    previous_event_hash TEXT,
    event_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ledger_checkpoints (
    sequence BIGINT PRIMARY KEY,
    event_hash TEXT NOT NULL,
    controller_epoch BIGINT NOT NULL,
    signature TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS runtime_drift_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment TEXT NOT NULL,
    component TEXT NOT NULL,
    expected_state JSONB NOT NULL,
    observed_state JSONB NOT NULL,
    drift_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);
