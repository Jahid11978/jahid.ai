from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from backend.control_plane.models import Artifact, Component, Release
from backend.control_plane.orchestrator import ReleaseOrchestrator
from backend.control_plane.policy import Policy
from backend.ledger.writer import AuditLedger


def load(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_release(data: dict) -> Release:
    artifact = Artifact(**data["artifact"])
    components = [Component(**item) for item in data["components"]]
    return Release(
        release_id=data["release_id"],
        artifact=artifact,
        components=components,
        schema_version=data.get("schema_version", ""),
        policy_version=data.get("policy_version", ""),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("--environment", default=os.environ.get("TARGET_ENVIRONMENT", "staging"))
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()

    manifest = load(args.manifest)
    evidence = load(args.evidence)
    release = build_release(manifest)
    policy_data = load(f"policies/{args.environment}.json")
    policy = Policy(environment=args.environment, **policy_data)
    ledger = AuditLedger()
    controller = ReleaseOrchestrator(ledger, policy)
    controller.validate(release, evidence)
    plan = controller.plan(release)
    print(json.dumps({"release": release.release_id, "environment": args.environment, "promotion_order": plan, "ledger_head": ledger.head}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
