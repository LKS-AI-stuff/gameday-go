"""Fixtures for tests against a real Postgres (local Supabase, or the CI service container)."""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import pytest
from alembic import command
from alembic.config import Config

from app.cli import _asyncpg_dsn, bootstrap_db
from app.core.settings import Settings, get_settings

BACKEND_DIR = Path(__file__).resolve().parents[2]


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
