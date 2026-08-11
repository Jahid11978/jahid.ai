from __future__ import annotations

from .client import CloudflareClient


def create_percentage_deployment(client: CloudflareClient, script_name: str, versions: list[dict], message: str) -> dict:
    if not versions or len(versions) > 2:
        raise ValueError("Cloudflare Workers deployments support one or two versions")
    total = sum(float(item["percentage"]) for item in versions)
    if abs(total - 100.0) > 1e-9:
        raise ValueError("deployment percentages must total 100")
    if any(float(item["percentage"]) <= 0 for item in versions):
        raise ValueError("deployment percentages must be greater than zero")
    return client.request("POST", f"/accounts/{client.account_id}/workers/scripts/{script_name}/deployments", {
        "strategy": "percentage",
        "versions": versions,
        "annotations": {"workers/message": message, "workers/triggered_by": "jahid-ai-release-controller"},
    })


def list_deployments(client: CloudflareClient, script_name: str) -> dict:
    return client.request("GET", f"/accounts/{client.account_id}/workers/scripts/{script_name}/deployments")


def promote_100(client: CloudflareClient, script_name: str, version_id: str, message: str) -> dict:
    return create_percentage_deployment(client, script_name, [{"percentage": 100, "version_id": version_id}], message)
