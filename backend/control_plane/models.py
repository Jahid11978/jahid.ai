from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Artifact:
    digest: str
    source_commit: str
    sbom_digest: str
    provenance_digest: str
    signature_digest: str


@dataclass(frozen=True)
class Component:
    name: str
    kind: str
    artifact_digest: str | None = None
    version_id: str | None = None
    depends_on: tuple[str, ...] = ()
    rollback_strategy: str = "immutable_artifact"


@dataclass
class Release:
    release_id: str
    artifact: Artifact
    components: list[Component] = field(default_factory=list)
    schema_version: str = ""
    policy_version: str = ""

    def component_map(self) -> dict[str, Component]:
        return {component.name: component for component in self.components}


@dataclass(frozen=True)
class Decision:
    status: str
    reasons: tuple[str, ...] = ()
    created_at: str = field(default_factory=utc_now)


class ReleaseError(RuntimeError):
    pass
