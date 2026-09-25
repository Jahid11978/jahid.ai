from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass


class CloudflareError(RuntimeError):
    pass


@dataclass
class CloudflareClient:
    api_token: str
    account_id: str

    @classmethod
    def from_env(cls) -> "CloudflareClient":
        token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
        account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
        if not token or not account:
            raise CloudflareError("CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID are required")
        return cls(token, account)

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        url = "https://api.cloudflare.com/client/v4" + path
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(url, data=data, method=method.upper())
        request.add_header("Authorization", f"Bearer {self.api_token}")
        request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise CloudflareError(f"Cloudflare API {exc.code}: {detail}") from exc
        if not body.get("success"):
            raise CloudflareError(json.dumps(body.get("errors", body)))
        return body

    def trigger_zone_activation_check(self, zone_id: str) -> dict:
        return self.request("PUT", f"/zones/{zone_id}/activation_check")
