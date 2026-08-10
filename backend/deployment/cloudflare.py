from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx


class CloudflareAPIError(RuntimeError):
    pass


class CloudflareAdapter:
    """Cloudflare adapter with idempotent reads, retry/backoff, and activation-check support."""

    def __init__(self, api_token: str, account_id: str | None = None, zone_id: str | None = None) -> None:
        self.api_token = api_token
        self.account_id = account_id
        self.zone_id = zone_id
        self.base = "https://api.cloudflare.com/client/v4"

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.api_token}"
        headers["Content-Type"] = "application/json"

        for attempt in range(5):
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.request(method, self.base + path, headers=headers, **kwargs)
                if response.status_code in {408, 429} or response.status_code >= 500:
                    raise httpx.HTTPStatusError("retryable Cloudflare response", request=response.request, response=response)
                response.raise_for_status()
                payload = response.json()
                if not payload.get("success"):
                    raise CloudflareAPIError(str(payload.get("errors", [])))
                return payload
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                if attempt == 4:
                    raise CloudflareAPIError(str(exc)) from exc
                delay = min(30.0, 2 ** attempt) + random.random()
                await asyncio.sleep(delay)
        raise CloudflareAPIError("unreachable")

    async def trigger_activation_check(self) -> dict:
        if not self.zone_id:
            raise CloudflareAPIError("zone_id is required for activation checks")
        return await self._request("PUT", f"/zones/{self.zone_id}/activation_check")

    async def observe(self, environment: str) -> dict:
        if not self.account_id:
            raise CloudflareAPIError("account_id is required")
        return await self._request("GET", f"/accounts/{self.account_id}/workers/scripts")

    async def promote_existing(self, environment: str, version_id: str, percentage: int) -> dict:
        # Promotion must be implemented against the configured Cloudflare product's
        # version/deployment endpoint. This adapter deliberately refuses to invent
        # an endpoint or rebuild an artifact when no deployment contract is configured.
        raise CloudflareAPIError(
            "No configured version-promotion endpoint. Register the exact Cloudflare "
            "deployment API contract before enabling mutations."
        )

    async def rollback_existing(self, environment: str, version_id: str) -> dict:
        raise CloudflareAPIError(
            "No configured version-rollback endpoint. Register the exact Cloudflare "
            "deployment API contract before enabling mutations."
        )
