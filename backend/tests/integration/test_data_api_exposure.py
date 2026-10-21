"""The Supabase Data API never returns app data (TDD §6.1).

Runs against the local stack (`uv run pytest -m supabase`) and, in M6, against the
hosted project as a smoke test. Also checks that a real Supabase token passes our
verifier (open item T3).
"""

import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.auth import TokenVerifier
from app.core.settings import REPO_ROOT, get_settings

pytestmark = pytest.mark.supabase

APP_TABLES = ("users", "alembic_version")


class StackSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")
    supabase_url: str
    supabase_publishable_key: SecretStr
    supabase_secret_key: SecretStr


@pytest.fixture(scope="module")
def stack() -> StackSettings:
    return StackSettings()


@pytest.fixture(scope="module")
async def user_token(stack: StackSettings) -> AsyncIterator[str]:
    """A confirmed test user, signed in with a password; deleted afterwards."""
    admin = {"apikey": stack.supabase_secret_key.get_secret_value()}
    public = {"apikey": stack.supabase_publishable_key.get_secret_value()}
    email = f"exposure-test-{uuid.uuid4().hex[:8]}@example.com"
    password = uuid.uuid4().hex
    async with httpx.AsyncClient(base_url=stack.supabase_url, timeout=10) as client:
        created = await client.post(
            "/auth/v1/admin/users",
            headers=admin,
            json={
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"age_confirmed": True},
            },
        )
        assert created.status_code == 200, created.text
        user_id = created.json()["id"]
        try:
            session = await client.post(
                "/auth/v1/token",
                params={"grant_type": "password"},
                headers=public,
                json={"email": email, "password": password},
            )
            assert session.status_code == 200, session.text
            yield session.json()["access_token"]
        finally:
            await client.delete(f"/auth/v1/admin/users/{user_id}", headers=admin)


def assert_no_data(response: httpx.Response) -> None:
    # Data API disabled → 404/503; otherwise only permission or unknown-relation errors.
    assert response.status_code in (401, 403, 404, 406, 503), (response.status_code, response.text)
    assert not (
        response.headers.get("content-type", "").startswith("application/json")
        and isinstance(response.json(), list)
    )


@pytest.mark.parametrize("table", APP_TABLES)
@pytest.mark.parametrize("profile", [None, "app"])
async def test_anon_key_gets_no_data(stack: StackSettings, table: str, profile: str | None) -> None:
    headers = {"apikey": stack.supabase_publishable_key.get_secret_value()}
    if profile:
        headers["Accept-Profile"] = profile
    async with httpx.AsyncClient(base_url=stack.supabase_url, timeout=10) as client:
        assert_no_data(await client.get(f"/rest/v1/{table}", headers=headers))


@pytest.mark.parametrize("table", APP_TABLES)
@pytest.mark.parametrize("profile", [None, "app"])
async def test_user_token_gets_no_data(
    stack: StackSettings, user_token: str, table: str, profile: str | None
) -> None:
    headers = {
        "apikey": stack.supabase_publishable_key.get_secret_value(),
        "Authorization": f"Bearer {user_token}",
    }
    if profile:
        headers["Accept-Profile"] = profile
    async with httpx.AsyncClient(base_url=stack.supabase_url, timeout=10) as client:
        assert_no_data(await client.get(f"/rest/v1/{table}", headers=headers))


async def test_real_supabase_token_passes_our_verifier(user_token: str) -> None:
    verifier = TokenVerifier(get_settings())
    try:
        claims = await verifier.verify(user_token)
    finally:
        await verifier.aclose()
    assert claims.age_confirmed is True
