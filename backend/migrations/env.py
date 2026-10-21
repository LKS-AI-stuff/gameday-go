"""Alembic environment. Runs as the backend role, so it owns every table it creates."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.settings import get_settings
from app.db import models  # noqa: F401  (registers tables on the metadata)
from app.db.base import APP_SCHEMA, Base
from migrations.hardening import REASSERT_REVOKES

if context.config.config_file_name:
    fileConfig(context.config.config_file_name)

target_metadata = Base.metadata


def _run(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=APP_SCHEMA,
        include_schemas=True,
        include_name=lambda name, type_, _: type_ != "schema" or name == APP_SCHEMA,
    )
    with context.begin_transaction():
        context.run_migrations()
        # Final hardening step of every migration run (TDD §6.1, layer 3).
        connection.execute(text(REASSERT_REVOKES))


async def _run_async() -> None:
    engine = create_async_engine(get_settings().database_url.get_secret_value())
    async with engine.connect() as connection:
        await connection.execute(text(f"SET search_path TO {APP_SCHEMA}"))
        await connection.run_sync(_run)
        await connection.commit()
    await engine.dispose()


if context.is_offline_mode():
    raise SystemExit("Offline migrations aren't supported; run against a database.")
asyncio.run(_run_async())
