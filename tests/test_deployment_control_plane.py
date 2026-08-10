import pytest

from backend.deployment.controller import PromotionBlocked, PromotionController, Release
from backend.deployment.event_chain import ChainEvent, EventChain
from backend.deployment.policy import DEFAULT_POLICIES


def release(**overrides):
    values = dict(
        artifact_id="artifact-1",
        artifact_digest="sha256:abc",
        commit_sha="deadbeef",
        cloudflare_version_id="version-1",
        provenance_verified=True,
        signature_verified=True,
        sbom_verified=True,
    )
    values.update(overrides)
    return Release(**values)


def test_event_chain_detects_tampering():
    chain = EventChain()
    chain.append(ChainEvent("A", "production", "test", {"n": 1}))
    chain.append(ChainEvent("B", "production", "test", {"n": 2}))
    assert chain.verify()
    event, previous, digest = chain._events[0]
    chain._events[0] = (ChainEvent("A", "production", "test", {"n": 9}), previous, digest)
    assert not chain.verify()


def test_production_requires_human_approval():
    controller = PromotionController(adapter=None)
    with pytest.raises(PromotionBlocked):
        controller.admit("production", release(), human_approved=False)


def test_production_policy_is_fail_closed_for_drift():
    policy = DEFAULT_POLICIES["production"]
    assert policy.require_human_approval is True
    assert policy.can_auto_repair_drift is False
    assert policy.rollout_percentages == (5, 10, 25, 50, 100)


def test_unverified_release_is_blocked():
    controller = PromotionController(adapter=None)
    with pytest.raises(PromotionBlocked):
        controller.admit("production", release(signature_verified=False), human_approved=True)
