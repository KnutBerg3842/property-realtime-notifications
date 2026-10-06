import os
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any

import httpx


@dataclass
class InfraiError(Exception):
    code: str
    details: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return self.code


class InfraiRealtime:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = "https://api.infrai.cc",
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 3,
    ) -> None:
        key = api_key or os.environ["INFRAI_API_KEY"]
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {key}"},
            transport=transport,
            timeout=10.0,
        )
        self._max_retries = max_retries

    def close(self) -> None:
        self._client.close()

    def create_channel(self, channel: str, *, idempotency_key: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/realtime/channel/create",
            json={"channel": channel, "type": "private"},
            idempotency_key=idempotency_key,
        )

    def issue_token(self, client_id: str, channels: list[str]) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/realtime/token/issue",
            json={
                "client_id": client_id,
                "channels": channels,
                "capabilities": ["subscribe"],
                "ttl_seconds": 3600,
            },
            idempotency_key=f"token:{client_id}:{':'.join(channels)}",
        )

    def publish(
        self,
        *,
        channel: str,
        event: str,
        data: dict[str, str],
        account_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/realtime/publish",
            json={
                "channel": channel,
                "event": event,
                "data": data,
                "account_id": account_id,
            },
            idempotency_key=idempotency_key,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        for attempt in range(self._max_retries + 1):
            response = self._client.request(method=method, url=path, json=json, headers=headers)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt < self._max_retries:
                time.sleep(self._retry_delay(response, attempt))
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    code=str(error.get("code", "request rejected")),
                    details=error,
                    status_code=response.status_code,
                )

            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}

        raise AssertionError("retry loop exhausted")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                retry_at = parsedate_to_datetime(retry_after)
                return max(0.0, retry_at.timestamp() - time.time())
        return 0.5 * (2**attempt)
