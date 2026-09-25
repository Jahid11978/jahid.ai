from __future__ import annotations

from .client import CloudflareClient
from .deployments import promote_100


def rollback_worker(client: CloudflareClient, script_name: str, lkg_version_id: str) -> dict:
    return promote_100(
        client,
        script_name,
        lkg_version_id,
        "JAHID.AI LKG rollback",
    )
