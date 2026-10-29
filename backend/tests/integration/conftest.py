"""Fixtures for tests against a real Postgres (local Supabase, or the CI service container)."""

import asyncio
import uuid
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import asyncpg
import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.cli import _asyncpg_dsn, bootstrap_db
from app.core.auth import TokenVerifier
from app.core.settings import Settings, get_settings
from app.core.supabase_admin import SupabaseAdmin
from app.db.session import get_sessionmaker
from app.main_api import create_app
from app.modules.schedule import reference
from app.modules.schedule import service as schedule_service
from app.modules.schedule.reference import load_overrides
from app.modules.schedule.sync import schedule_sync
from app.providers.apisports.mock import FixtureScheduleProvider, load_fixture
from tests.conftest import TokenFactory, make_settings

BACKEND_DIR = Path(__file__).resolve().parents[2]


async def _ensure_test_database(settings: Settings) -> None:
    """Creates the `<database>_test` database the tests run against (see tests/conftest.py)."""
    assert settings.database_admin_url is not None, "DATABASE_ADMIN_URL is required"
    name = make_url(settings.database_url.get_secret_value()).database
    conn = await asyncpg.connect(_asyncpg_dsn(settings.database_admin_url.get_secret_value()))
    try:
        if not await conn.fetchval("select 1 from pg_database where datname = $1", name):
            await conn.execute(f'CREATE DATABASE "{name}"')
    finally:
        await conn.close()


async def _ensure_data_api_roles(settings: Settings) -> None:
    """Plain Postgres (CI) has no Supabase roles; create them so grants can be checked."""
    assert settings.database_admin_url is not None, "DATABASE_ADMIN_URL is required"
    conn = await asyncpg.connect(_asyncpg_dsn(settings.database_admin_url.get_secret_value()))
    try:
        for role in ("anon", "authenticated"):
            if not await conn.fetchval("select 1 from pg_roles where rolname = $1", role):
                await conn.execute(f"CREATE ROLE {role} NOLOGIN")
    finally:
        await conn.close()


@pytest.fixture(scope="session")
def migrated_db() -> Settings:
    """Bootstrap the backend role and run `alembic upgrade head` once per session."""
    settings = get_settings()
    asyncio.run(_ensure_test_database(settings))
    asyncio.run(_ensure_data_api_roles(settings))
    asyncio.run(bootstrap_db())
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    command.upgrade(config, "head")
    return settings


@pytest.fixture
async def app_conn(migrated_db: Settings) -> AsyncIterator[asyncpg.Connection]:
    """A connection as the backend role (gamedaygo_app)."""
    conn = await asyncpg.connect(_asyncpg_dsn(migrated_db.database_url.get_secret_value()))
    try:
        yield conn
    finally:
        await conn.close()


# ---- API client and users


@pytest.fixture
async def api(
    migrated_db: Settings, jwks: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(migrated_db)
    # Tokens are minted with the test key; JWKS is served from memory.
    jwks_client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=jwks))
    )
    app.state.token_verifier = TokenVerifier(make_settings(), http_client=jwks_client)
    # The Auth Admin API is mocked per test (account deletion); default: user deleted.
    admin_client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(204)))
    app.state.supabase_admin = SupabaseAdmin(
        make_settings(supabase_secret_key="test-secret"), http_client=admin_client, retry_base_s=0
    )
    # Browsing results depend on "now" (planning window, current week): freeze it.
    monkeypatch.setattr(schedule_service, "utcnow", lambda: NOW)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await jwks_client.aclose()
    await admin_client.aclose()


@pytest.fixture
async def user_ids(app_conn: asyncpg.Connection) -> AsyncIterator[list[str]]:
    """Collects user IDs created by a test and deletes their rows afterwards."""
    ids: list[str] = []
    yield ids
    if ids:
        await app_conn.execute("delete from app.users where id = any($1::uuid[])", ids)


@pytest.fixture
def new_user(make_token: TokenFactory, user_ids: list[str]) -> Callable[..., dict[str, str]]:
    """Auth headers for a fresh user, cleaned up after the test."""

    def factory(**claims: Any) -> dict[str, str]:
        sub = str(uuid.uuid4())
        user_ids.append(sub)
        return auth(make_token(sub=sub, **claims))

    return factory


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---- Reference data and the recorded 2026 season (API-Sports fixtures)

# The recorded schedule was fetched 2026-10-29; tests browse it as of that day.
NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)
SEASON = 2026


def fixture_provider() -> FixtureScheduleProvider:
    return FixtureScheduleProvider({SEASON: load_fixture("games_2026")}, now=NOW)


@pytest.fixture(scope="session")
async def reference_data(migrated_db: Settings) -> Settings:
    """ZIPs, places, teams (from fixtures) and rivalries, once per session."""
    async with get_sessionmaker()() as session:
        await reference.seed_centroids(session)
        await reference.seed_teams(session, fixture_provider(), SEASON, load_overrides())
        await reference.seed_rivalries(session)
        await session.commit()
    return migrated_db


async def reset_season() -> None:
    """Replace any schedule data with the recorded 2026 season, synced by `schedule_sync`."""
    async with get_sessionmaker()() as session:
        await session.execute(text("DELETE FROM app.seasons"))
        await session.execute(text("DELETE FROM app.games"))
        await session.commit()
    result = await schedule_sync(get_sessionmaker(), fixture_provider(), get_settings(), now=NOW)
    assert result.status == "succeeded", result


@pytest.fixture(scope="session")
async def season_data(reference_data: Settings) -> Settings:
    await reset_season()
    return reference_data
