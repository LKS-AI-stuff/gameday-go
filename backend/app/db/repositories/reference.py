"""Reference data: ZIP and place centroids, teams, rivalries, venues (TDD §7.1). Not user-owned."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FeaturedRivalry, PlaceCentroid, Team, VenueRef, ZipCentroid


async def _copy_upsert(
    session: AsyncSession,
    table: str,
    columns: Sequence[str],
    key: Sequence[str],
    records: Sequence[tuple[Any, ...]],
) -> None:
    """Bulk upsert through COPY into a temp table (tens of thousands of rows in a second)."""
    conn = await session.connection()
    temp = f"tmp_{table}"
    cols = ", ".join(columns)
    # Through SQLAlchemy, so it runs inside the session's transaction (ON COMMIT DROP).
    await conn.exec_driver_sql(
        f"CREATE TEMP TABLE {temp} (LIKE app.{table} INCLUDING DEFAULTS) ON COMMIT DROP"
    )
    raw = (await conn.get_raw_connection()).driver_connection
    assert raw is not None
    await raw.copy_records_to_table(temp, records=records, columns=list(columns))
    updates = ", ".join(f"{c} = excluded.{c}" for c in columns if c not in key)
    await conn.exec_driver_sql(
        f"INSERT INTO app.{table} ({cols}) SELECT {cols} FROM {temp} "  # noqa: S608
        f"ON CONFLICT ({', '.join(key)}) DO UPDATE SET {updates}, updated_at = now()"
    )


async def upsert_places(
    session: AsyncSession, rows: Sequence[tuple[str, str, float, float]]
) -> None:
    await _copy_upsert(
        session, "place_centroids", ("name", "state", "lat", "lng"), ("name", "state"), rows
    )


async def upsert_zips(
    session: AsyncSession, rows: Sequence[tuple[str, float, float, str, str]]
) -> None:
    await _copy_upsert(
        session, "zip_centroids", ("zip", "lat", "lng", "place_name", "state"), ("zip",), rows
    )


async def get_zip(session: AsyncSession, zip_code: str) -> ZipCentroid | None:
    return await session.get(ZipCentroid, zip_code)


async def zips_near(
    session: AsyncSession, lat: float, lng: float, lat_span: float, lng_span: float
) -> list[ZipCentroid]:
    rows = await session.scalars(
        select(ZipCentroid).where(
            ZipCentroid.lat.between(lat - lat_span, lat + lat_span),
            ZipCentroid.lng.between(lng - lng_span, lng + lng_span),
        )
    )
    return list(rows)


async def get_place(session: AsyncSession, name: str, state: str) -> PlaceCentroid | None:
    return await session.get(PlaceCentroid, (name, state))


async def counts(session: AsyncSession) -> dict[str, int]:
    result: dict[str, int] = {}
    for model in (PlaceCentroid, ZipCentroid, Team, FeaturedRivalry):
        result[model.__tablename__] = (
            await session.scalar(select(func.count()).select_from(model)) or 0
        )
    return result


# ---- Teams and rivalries


async def list_teams(session: AsyncSession) -> list[Team]:
    rows = await session.scalars(select(Team).order_by(Team.conference, Team.division, Team.name))
    return list(rows)


async def existing_team_ids(session: AsyncSession, ids: Sequence[str]) -> set[str]:
    rows = await session.scalars(select(Team.id).where(Team.id.in_(ids)))
    return set(rows)


async def upsert_team(session: AsyncSession, values: dict[str, Any]) -> None:
    stmt = insert(Team).values(**values)
    update = {k: stmt.excluded[k] for k in values if k != "id"}
    await session.execute(
        stmt.on_conflict_do_update(
            index_elements=[Team.id], set_={**update, "updated_at": func.now()}
        )
    )


async def update_team(session: AsyncSession, team_id: str, values: dict[str, Any]) -> None:
    team = await session.get(Team, team_id)
    if team is not None:
        for key, value in values.items():
            setattr(team, key, value)


async def replace_rivalries(session: AsyncSession, rows: Sequence[tuple[str, str, str]]) -> None:
    await session.execute(delete(FeaturedRivalry))
    for team_a, team_b, reason in rows:
        a, b = sorted((team_a, team_b))
        session.add(FeaturedRivalry(team_a=a, team_b=b, reason=reason))


async def rivalries(session: AsyncSession) -> list[FeaturedRivalry]:
    return list(await session.scalars(select(FeaturedRivalry)))


# ---- Venues


async def upsert_venue(session: AsyncSession, values: dict[str, Any]) -> VenueRef:
    stmt = insert(VenueRef).values(**values)
    update = {k: stmt.excluded[k] for k in values if k not in ("name", "city")}
    venue: VenueRef | None = await session.scalar(
        stmt.on_conflict_do_update(
            constraint="uq_venues_ref_name_city", set_={**update, "updated_at": func.now()}
        ).returning(VenueRef)
    )
    assert venue is not None
    return venue
