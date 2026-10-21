"""The single path for outbound provider calls (TDD §8.2).

Implemented now: kill switch (1), timeouts and retries (4), redaction (5) and
call metrics (6). The daily budget (2) and rate limiter (3) are added with the
first provider integration in M1.
"""

import time
from collections.abc import Mapping
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.core.logging import get_logger
from app.core.redaction import redact_text
from app.core.settings import Provider, Settings

log = get_logger(__name__)

DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
MAX_ATTEMPTS = 3
MAX_RETRY_AFTER_S = 30.0


class ProviderDisabled(Exception):
    def __init__(self, provider: Provider) -> None:
        super().__init__(f"provider {provider} is disabled")
        self.provider = provider


class RetryableStatus(Exception):
    def __init__(self, response: httpx.Response) -> None:
        super().__init__(f"retryable status {response.status_code}")
        self.response = response


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, RetryableStatus | httpx.TransportError)


def _wait(base: float) -> Any:
    backoff = wait_exponential(multiplier=base, max=10 * base if base else 0)

    def wait(state: RetryCallState) -> float:
        exc = state.outcome.exception() if state.outcome else None
        if isinstance(exc, RetryableStatus) and exc.response.status_code == 429:
            retry_after = exc.response.headers.get("Retry-After", "")
            if retry_after.isdigit():
                return min(float(retry_after), MAX_RETRY_AFTER_S)
        return float(backoff(state))

    return wait


class ProviderClient:
    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
        retry_base_s: float = 0.5,
    ) -> None:
        self._settings = settings
        self._client = client or httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
        self._retry_base_s = retry_base_s

    async def aclose(self) -> None:
        await self._client.aclose()

    async def request(
        self,
        provider: Provider,
        method: str,
        url: str,
        *,
        endpoint: str,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        json: Any = None,
    ) -> httpx.Response:
        """Send one logical request. `endpoint` is a short name used in logs instead of the URL."""
        if not self._settings.provider_enabled(provider):
            raise ProviderDisabled(provider)

        started = time.monotonic()
        response: httpx.Response | None = None
        try:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception(_is_retryable),
                stop=stop_after_attempt(MAX_ATTEMPTS),
                wait=_wait(self._retry_base_s),
                reraise=True,
            ):
                with attempt:
                    response = await self._client.request(
                        method, url, params=params, headers=headers, json=json
                    )
                    if response.status_code == 429 or response.status_code >= 500:
                        raise RetryableStatus(response)
        except RetryableStatus as exc:
            response = exc.response
        except httpx.TransportError as exc:
            log.warning(
                "provider_call_failed",
                provider=provider,
                endpoint=endpoint,
                error=redact_text(str(exc)),
                latency_ms=round((time.monotonic() - started) * 1000),
            )
            raise

        assert response is not None
        log.info(
            "provider_call",
            provider=provider,
            endpoint=endpoint,
            status=response.status_code,
            latency_ms=round((time.monotonic() - started) * 1000),
        )
        return response
