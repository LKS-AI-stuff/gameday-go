"""Operator commands: uv run python -m app.cli <command>."""

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import asyncpg
from sqlalchemy.engine import make_url

from app.core.logging import configure_logging
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


def build_centroids(zcta: Path, places: Path) -> None:
    from app.modules.schedule.centroids import DATA_DIR, build

    zips, place_count = build(zcta, places)
    print(f"Wrote {zips} ZIPs and {place_count} places to {DATA_DIR}")


async def seed(refresh_teams: bool) -> None:
    """Reference data (TDD §7.1): places, ZIPs, teams (2 API-Sports requests), rivalries."""
    from app.db.repositories import reference as reference_repo
    from app.db.session import get_sessionmaker
    from app.domain.season import default_season
    from app.modules.schedule import reference
    from app.providers.factory import provider_client, schedule_provider

    settings = get_settings()
    overrides = reference.load_overrides()
    async with get_sessionmaker()() as session:
        zips, places = await reference.seed_centroids(session)
        await session.commit()
        print(f"Places: {places}. ZIPs: {zips}.")
        teams = await reference_repo.list_teams(session)
        if len(teams) < 32 or refresh_teams:
            client = provider_client(settings)
            try:
                provider = schedule_provider(settings, client)
                season = default_season(datetime.now(UTC))
                count = await reference.seed_teams(session, provider, season, overrides)
            finally:
                await client.aclose()
            await session.commit()
            print(f"Teams: {count} (from API-Sports, season {season}).")
        else:
            print(f"Teams: {len(teams)} already seeded (use --refresh-teams to reload).")
        print(f"Featured rivalries: {await reference.seed_rivalries(session)}.")
        await session.commit()


async def sync_schedule(season: int | None) -> int:
    from app.db.session import get_sessionmaker
    from app.modules.schedule.sync import schedule_sync
    from app.providers.factory import provider_client, schedule_provider

    settings = get_settings()
    client = provider_client(settings)
    try:
        provider = schedule_provider(settings, client)
        result = await schedule_sync(get_sessionmaker(), provider, settings, season=season)
    finally:
        await client.aclose()
    print(
        f"Schedule sync {result.status}: seasons {list(result.seasons)}, "
        f"{result.records} games, {result.changes} changes"
        + (f", error {result.error}" if result.error else "")
    )
    return 0 if result.status == "succeeded" else 1


async def budgets_report() -> None:
    from sqlalchemy import select

    from app.db.models import ProviderBudget
    from app.db.session import get_sessionmaker

    async with get_sessionmaker()() as session:
        rows = await session.scalars(
            select(ProviderBudget).order_by(ProviderBudget.day.desc()).limit(14)
        )
        for b in rows:
            remaining = b.daily_limit - b.reserved - b.used
            print(
                f"{b.day} {b.provider}: used {b.used} of {b.daily_limit} "
                f"(reserved {b.reserved}, remaining {remaining})"
            )


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
    centroids = sub.add_parser(
        "build-centroids", help="Convert Census gazetteers into data/*_centroids.csv"
    )
    centroids.add_argument("zcta", type=Path)
    centroids.add_argument("places", type=Path)
    seed_cmd = sub.add_parser("seed", help="Load reference data (places, ZIPs, teams, rivalries)")
    seed_cmd.add_argument("--refresh-teams", action="store_true")
    sync = sub.add_parser("sync-schedule", help="Sync the active season's schedule")
    sync.add_argument("--season", type=int)
    sub.add_parser("budgets", help="Show provider request budgets")
    args = parser.parse_args()

    if args.command in ("seed", "sync-schedule", "budgets"):
        configure_logging(get_settings().log_level)
    if args.command == "bootstrap-db":
        asyncio.run(bootstrap_db())
    elif args.command == "export-openapi":
        export_openapi(args.path)
    elif args.command == "build-centroids":
        build_centroids(args.zcta, args.places)
    elif args.command == "seed":
        asyncio.run(seed(args.refresh_teams))
    elif args.command == "sync-schedule":
        sys.exit(asyncio.run(sync_schedule(args.season)))
    elif args.command == "budgets":
        asyncio.run(budgets_report())


if __name__ == "__main__":
    main()
