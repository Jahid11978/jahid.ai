from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .event_chain import ChainEvent, EventChain
from .policy import policy_for


class DeploymentAdapter(Protocol):
    async def observe(self, environment: str) -> dict: ...
    async def promote_existing(self, environment: str, version_id: str, percentage: int) -> dict: ...
    async def rollback_existing(self, environment: str, version_id: str) -> dict: ...


@dataclass(frozen=True)
class Release:
    artifact_id: str
    artifact_digest: str
    commit_sha: str
    cloudflare_version_id: str
    provenance_verified: bool
    signature_verified: bool
    sbom_verified: bool


class PromotionBlocked(RuntimeError):
    pass


class PromotionController:
    """Crash-safe decision layer. Promotion never builds or mutates source."""

    def __init__(self, adapter: DeploymentAdapter, chain: EventChain | None = None) -> None:
        self.adapter = adapter
        self.chain = chain or EventChain()

    def admit(self, environment: str, release: Release, human_approved: bool = False) -> None:
        policy = policy_for(environment)
        if not release.provenance_verified:
            raise PromotionBlocked("release provenance is not verified")
        if not release.signature_verified:
            raise PromotionBlocked("release signature is not verified")
        if not release.sbom_verified:
            raise PromotionBlocked("release SBOM is not verified")
        if policy.require_human_approval and not human_approved:
            raise PromotionBlocked("human approval is required")

    async def reconcile(self, environment: str, release: Release) -> dict:
        observed = await self.adapter.observe(environment)
        desired = release.cloudflare_version_id
        current = observed.get("version_id")
        percentage = int(observed.get("percentage", 0))

        if current == desired and percentage == 100:
            self.chain.append(ChainEvent(
                "RECONCILED", environment, "promotion-controller",
                {"status": "in_sync"}, release.artifact_digest, desired
            ))
            return {"status": "IN_SYNC", "version_id": desired}

        if current != desired:
            self.chain.append(ChainEvent(
                "DRIFT_DETECTED", environment, "reconciliation-controller",
                {"current": current, "desired": desired}, release.artifact_digest, desired
            ))
            return {"status": "DRIFT_REQUIRES_REVIEW", "current": current, "desired": desired}

        if policy_for(environment).can_auto_repair_drift:
            result = await self.adapter.promote_existing(environment, desired, 100)
            self.chain.append(ChainEvent(
                "DRIFT_REPAIRED", environment, "reconciliation-controller",
                {"previous_percentage": percentage, "result": result}, release.artifact_digest, desired
            ))
            return {"status": "REPAIRED", "result": result}

        return {"status": "DRIFT_REQUIRES_REVIEW"}

    async def promote(self, environment: str, release: Release, human_approved: bool = False) -> dict:
        self.admit(environment, release, human_approved)
        policy = policy_for(environment)
        results = []
        for percentage in policy.rollout_percentages:
            result = await self.adapter.promote_existing(
                environment, release.cloudflare_version_id, percentage
            )
            results.append({"percentage": percentage, "result": result})
            self.chain.append(ChainEvent(
                "PROMOTED", environment, "promotion-controller",
                {"percentage": percentage}, release.artifact_digest, release.cloudflare_version_id
            ))
        self.chain.append(ChainEvent(
            "LKG_ELIGIBLE", environment, "promotion-controller",
            {"percentage": 100}, release.artifact_digest, release.cloudflare_version_id
        ))
        return {"status": "PROMOTED", "steps": results}
