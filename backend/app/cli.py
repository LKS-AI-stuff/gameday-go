"""Operator commands: uv run python -m app.cli <command>."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

import asyncpg
from sqlalchemy.engine import make_url

from app.core.settings import get_settings


def _asyncpg_dsn(sqlalchemy_url: str) -> str:
    return (
        make_url(sqlalchemy_url).set(drivername="postgresql").render_as_string(hide_password=False)
    )


async def bootstrap_db() -> None:
    """Create the backend role and schema `app` (TDD §6.1). Safe to re-run.

    Runs as the admin connection (DATABASE_ADMIN_URL). The role name and password
    come from DATABASE_URL, so the password only ever lives in `.env`.
    """
    settings = get_settings()
    if settings.database_admin_url is None:
        sys.exit("DATABASE_ADMIN_URL is required for bootstrap-db")
    app_url = make_url(settings.database_url.get_secret_value())
    role, password, database = app_url.username, app_url.password, app_url.database
    if not role or not password or not database:
        sys.exit("DATABASE_URL must include a user, password and database")

    admin = await asyncpg.connect(_asyncpg_dsn(settings.database_admin_url.get_secret_value()))
    try:
        exists = await admin.fetchval("select 1 from pg_roles where rolname = $1", role)
        verb = (
            "ALTER ROLE %I WITH LOGIN PASSWORD %L" if exists else "CREATE ROLE %I LOGIN PASSWORD %L"
        )
        await admin.execute(
            await admin.fetchval("select format($1, $2::text, $3::text)", verb, role, password)
        )
        # CREATE on the database is needed only to create the schema; it's revoked below.
        await admin.execute(
            await admin.fetchval(
                "select format('GRANT CONNECT, CREATE ON DATABASE %I TO %I', $1::text, $2::text)",
                database,
                role,
            )
        )
    finally:
        await admin.close()

    app_conn = await asyncpg.connect(_asyncpg_dsn(settings.database_url.get_secret_value()))
    try:
        await app_conn.execute("CREATE SCHEMA IF NOT EXISTS app")
        await app_conn.execute(
            """
            DO $$
            DECLARE r text;
            BEGIN
              FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                  EXECUTE format('REVOKE ALL ON SCHEMA app FROM %I', r);
                END IF;
              END LOOP;
              REVOKE ALL ON SCHEMA app FROM PUBLIC;
            END $$;
            """
        )
    finally:
        await app_conn.close()

    admin = await asyncpg.connect(_asyncpg_dsn(settings.database_admin_url.get_secret_value()))
    try:
        await admin.execute(
            await admin.fetchval(
                "select format('REVOKE CREATE ON DATABASE %I FROM %I', $1::text, $2::text)",
                database,
                role,
            )
        )
    finally:
        await admin.close()
    print(f"Role {role} and schema app are ready.")


def export_openapi(path: Path) -> None:
    from app.main_api import create_app

    schema = create_app().openapi()
    path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {path}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("bootstrap-db", help="Create the backend DB role and schema")
    openapi = sub.add_parser("export-openapi", help="Write the OpenAPI schema as JSON")
    openapi.add_argument("path", type=Path)
    args = parser.parse_args()

    if args.command == "bootstrap-db":
        asyncio.run(bootstrap_db())
    elif args.command == "export-openapi":
        export_openapi(args.path)


if __name__ == "__main__":
    main()
