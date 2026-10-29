"""Supabase Auth Admin API, for account deletion (FR-A4, TDD §6).

Supabase Auth is our own sign-in service, not a budgeted data provider, so like the JWKS fetch
in `core/auth.py` it doesn't go through `core/http.py`. The secret key is server-only and
never logged.
"""

import uuid

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.logging import get_logger
from app.core.settings import Settings

log = get_logger(__name__)


class AuthAdminError(Exception):
    pass


class SupabaseAdmin:
    def __init__(
        self,
        settings: Settings,
        http_client: httpx.AsyncClient | None = None,
        retry_base_s: float = 0.5,
    ) -> None:
        self._settings = settings
        self._http = http_client or httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
        self._retry_base_s = retry_base_s

    async def aclose(self) -> None:
        await self._http.aclose()

    async def delete_user(self, user_id: uuid.UUID) -> None:
        """Deletes the auth user; an already-deleted user (404) counts as done."""
        key = self._settings.supabase_secret_key
        if key is None:
            raise AuthAdminError("SUPABASE_SECRET_KEY is not set")
        url = f"{self._settings.supabase_url.rstrip('/')}/auth/v1/admin/users/{user_id}"
        try:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception_type((httpx.TransportError, AuthAdminError)),
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=self._retry_base_s, max=5),
                reraise=True,
            ):
                with attempt:
                    response = await self._http.delete(
                        url, headers={"apikey": key.get_secret_value()}
                    )
                    if response.status_code >= 500:
                        raise AuthAdminError(f"auth admin returned {response.status_code}")
        except (httpx.TransportError, AuthAdminError) as exc:
            log.warning("auth_user_delete_failed", error_type=type(exc).__name__)
            raise AuthAdminError("auth user deletion failed") from exc
        if response.status_code not in (200, 204, 404):
            log.warning("auth_user_delete_failed", status=response.status_code)
            raise AuthAdminError(f"auth admin returned {response.status_code}")
