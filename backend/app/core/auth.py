"""Supabase access-token verification (TDD §6).

Checks signature, expiry, issuer and audience. Keys come from the project's JWKS
endpoint (asymmetric signing, the default) or from the legacy shared secret.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Annotated, Any

import httpx
import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import ProblemError
from app.core.logging import get_logger
from app.core.settings import Settings

log = get_logger(__name__)

ASYMMETRIC_ALGORITHMS = frozenset({"ES256", "RS256"})
CLOCK_SKEW_S = 10
# Unknown key IDs trigger a refetch at most this often (key rotation without hammering Auth).
JWKS_MIN_REFRESH_S = 60


@dataclass(frozen=True)
class TokenClaims:
    user_id: uuid.UUID
    email: str
    # Set from sign-up form metadata; social sign-in users confirm separately (FR-A3).
    age_confirmed: bool


def _invalid(detail: str = "Invalid or expired access token") -> ProblemError:
    return ProblemError(401, "invalid_token", detail)


class TokenVerifier:
    def __init__(
        self,
        settings: Settings,
        http_client: httpx.AsyncClient | None = None,
        jwks_ttl_s: int = 600,
    ) -> None:
        self._settings = settings
        # Supabase Auth is our own sign-in service, not a budgeted data provider,
        # so it doesn't go through core/http.py.
        self._http = http_client or httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
        self._jwks_ttl_s = jwks_ttl_s
        self._keys: dict[str, jwt.PyJWK] = {}
        self._fetched_at = 0.0
        self._lock = asyncio.Lock()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def verify(self, token: str) -> TokenClaims:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise _invalid() from exc

        key = await self._key_for(header)
        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                key,
                algorithms=[header["alg"]],
                audience=self._settings.supabase_jwt_audience,
                issuer=self._settings.jwt_issuer,
                leeway=CLOCK_SKEW_S,
                options={"require": ["exp", "iat", "sub", "iss", "aud"]},
            )
        except jwt.PyJWTError as exc:
            raise _invalid() from exc

        if claims.get("role") != "authenticated" or claims.get("is_anonymous"):
            raise _invalid()
        try:
            user_id = uuid.UUID(claims["sub"])
        except ValueError as exc:
            raise _invalid() from exc
        email = claims.get("email")
        if not isinstance(email, str) or not email:
            raise _invalid()
        metadata = claims.get("user_metadata") or {}
        return TokenClaims(
            user_id=user_id,
            email=email,
            age_confirmed=metadata.get("age_confirmed") is True,
        )

    async def _key_for(self, header: dict[str, Any]) -> Any:
        alg = header.get("alg")
        if self._settings.supabase_jwt_mode == "secret":
            if alg != "HS256" or self._settings.supabase_jwt_secret is None:
                raise _invalid()
            return self._settings.supabase_jwt_secret.get_secret_value()

        kid = header.get("kid")
        if alg not in ASYMMETRIC_ALGORITHMS or not isinstance(kid, str):
            raise _invalid()
        key = await self._jwk(kid)
        if key is None:
            raise _invalid()
        return key.key

    async def _jwk(self, kid: str) -> jwt.PyJWK | None:
        now = time.monotonic()
        stale = now - self._fetched_at > self._jwks_ttl_s
        unknown = kid not in self._keys and now - self._fetched_at > JWKS_MIN_REFRESH_S
        if stale or unknown:
            async with self._lock:
                if time.monotonic() - self._fetched_at > JWKS_MIN_REFRESH_S or not self._keys:
                    await self._refresh()
        return self._keys.get(kid)

    async def _refresh(self) -> None:
        try:
            response = await self._http.get(self._settings.jwks_url)
            response.raise_for_status()
            keys = jwt.PyJWKSet.from_dict(response.json()).keys
        except (httpx.HTTPError, jwt.PyJWTError, ValueError) as exc:
            log.warning("jwks_fetch_failed", error_type=type(exc).__name__)
            if not self._keys:
                raise ProblemError(503, "auth_unavailable", "Sign-in service unavailable") from exc
            return
        self._keys = {k.key_id: k for k in keys if k.key_id}
        self._fetched_at = time.monotonic()


_bearer = HTTPBearer(auto_error=False)


async def current_claims(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> TokenClaims:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ProblemError(401, "not_authenticated", "Missing bearer token")
    verifier: TokenVerifier = request.app.state.token_verifier
    return await verifier.verify(credentials.credentials)
