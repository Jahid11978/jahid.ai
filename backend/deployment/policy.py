from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnvironmentPolicy:
    name: str
    require_human_approval: bool
    can_auto_repair_drift: bool
    rollout_percentages: tuple[int, ...]
    max_error_rate: float
    max_latency_ms: float


DEFAULT_POLICIES = {
    "development": EnvironmentPolicy(
        "development", False, True, (100,), 0.10, 5000
    ),
    "staging": EnvironmentPolicy(
        "staging", False, True, (25, 50, 100), 0.05, 3000
    ),
    "canary": EnvironmentPolicy(
        "canary", True, True, (5, 10, 25), 0.02, 2000
    ),
    "production": EnvironmentPolicy(
        "production", True, False, (5, 10, 25, 50, 100), 0.01, 1500
    ),
}


def policy_for(environment: str) -> EnvironmentPolicy:
    try:
        return DEFAULT_POLICIES[environment]
    except KeyError as exc:
        raise ValueError(f"Unsupported environment: {environment}") from exc
