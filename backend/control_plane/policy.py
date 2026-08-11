from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Policy:
    environment: str
    minimum_requests: int
    maximum_error_rate: float
    maximum_error_rate_delta: float
    maximum_p95_delta_ms: float
    required_approvals: int
    require_security_attestation: bool = True
    require_contract_tests: bool = True
    require_human_approval: bool = False


class PolicyError(RuntimeError):
    pass


def evaluate_admission(evidence: dict[str, Any], policy: Policy) -> None:
    required = {
        "artifact_verified": True,
        "signature_verified": True,
        "provenance_verified": True,
        "sbom_verified": True,
        "secrets_clean": True,
        "schema_compatible": True,
    }
    for key, expected in required.items():
        if evidence.get(key) is not expected:
            raise PolicyError(f"admission blocked: {key}")
    if policy.require_security_attestation and evidence.get("security_attestation") is not True:
        raise PolicyError("admission blocked: security_attestation")
    if policy.require_contract_tests and evidence.get("contract_tests") is not True:
        raise PolicyError("admission blocked: contract_tests")
    if policy.require_human_approval and evidence.get("human_approval") is not True:
        raise PolicyError("admission blocked: human_approval")


def evaluate_canary(stable: dict[str, float], canary: dict[str, float], policy: Policy) -> tuple[str, list[str]]:
    if canary.get("requests", 0) < policy.minimum_requests:
        return "WAIT", ["insufficient_sample"]
    reasons: list[str] = []
    error_rate = canary.get("error_rate", 1.0)
    error_delta = error_rate - stable.get("error_rate", 0.0)
    if error_rate > policy.maximum_error_rate:
        reasons.append("absolute_error_rate")
    if error_delta > policy.maximum_error_rate_delta:
        reasons.append("error_rate_regression")
    stable_p95 = stable.get("p95_ms")
    canary_p95 = canary.get("p95_ms")
    if stable_p95 is not None and canary_p95 is not None:
        if canary_p95 - stable_p95 > policy.maximum_p95_delta_ms:
            reasons.append("latency_regression")
    return ("ROLLBACK", reasons) if reasons else ("PROMOTE", [])
