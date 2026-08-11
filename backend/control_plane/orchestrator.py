from __future__ import annotations

from .models import Component, Release, ReleaseError


def promotion_order(release: Release) -> list[Component]:
    components = release.component_map()
    remaining = {name: set(component.depends_on) for name, component in components.items()}
    result: list[Component] = []
    while remaining:
        ready = sorted(name for name, deps in remaining.items() if not deps)
        if not ready:
            raise ReleaseError("release dependency cycle detected")
        for name in ready:
            result.append(components[name])
            del remaining[name]
        for deps in remaining.values():
            deps.difference_update(ready)
    return result


class ReleaseOrchestrator:
    def __init__(self, ledger, policy):
        self.ledger = ledger
        self.policy = policy

    def validate(self, release: Release, evidence: dict) -> None:
        from .policy import evaluate_admission
        evaluate_admission(evidence, self.policy)
        promotion_order(release)
        self.ledger.append({
            "event_type": "RELEASE_VALIDATED",
            "release_id": release.release_id,
            "artifact_digest": release.artifact.digest,
        })

    def plan(self, release: Release) -> list[str]:
        order = promotion_order(release)
        self.ledger.append({
            "event_type": "PROMOTION_PLAN_CREATED",
            "release_id": release.release_id,
            "components": [item.name for item in order],
        })
        return [item.name for item in order]
