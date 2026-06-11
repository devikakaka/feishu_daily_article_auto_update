"""Feishu Open API client with automatic token management."""

import time

import requests


class FeishuClient:
    """Handles authentication with Feishu Open API (tenant_access_token flow)."""

    def __init__(self, config: dict):
        self.app_id = config["feishu"]["app_id"]
        self.app_secret = config["feishu"]["app_secret"]
        self.base_url = config["feishu"]["base_url"]
        self._token = None
        self._token_expires = 0

    @property
    def token(self) -> str:
        """Get current tenant_access_token, refreshing if needed (60s safety buffer)."""
        if not self._token or time.time() >= self._token_expires - 60:
            self._refresh_token()
        return self._token

    def _refresh_token(self):
        """Refresh the tenant_access_token from Feishu."""
        url = f"{self.base_url}/open-apis/auth/v3/tenant_access_token/internal"
        resp = requests.post(
            url,
            json={
                "app_id": self.app_id,
                "app_secret": self.app_secret,
            },
            timeout=10,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Feishu auth failed: {data}")
        self._token = data["tenant_access_token"]
        # Token lifetime is 7200s (2 hours); refresh proactively
        self._token_expires = time.time() + data.get("expire", 7200)
        print(f"    Feishu token refreshed, expires in {data.get('expire', 7200)}s")

    def request(self, method: str, path: str, **kwargs) -> dict:
        """Make an authenticated request. Auto-injects Authorization header."""
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.token}"
        headers["Content-Type"] = "application/json; charset=utf-8"
        resp = requests.request(method, url, headers=headers, timeout=30, **kwargs)
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(
                f"Feishu API error [{method} {path}]: "
                f"code={data.get('code')}, msg={data.get('msg')}"
            )
        return data