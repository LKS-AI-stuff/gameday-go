"""Games, tags, changes, seasons and sync runs (TDD §7.3, §7.6). Not user-owned, except the
favorites filter, which takes the caller's `user_id` (FR-A5)."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Select, delete, func, or_, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Game,
    GameChange,
    GameTag,
    Season,
    SyncRun,
    UserFavoriteTeam,
    VenueRef,
)

# ---- Sync runs


async def start_sync_run(session: AsyncSession, kind: str, started_at: datetime) -> SyncRun:
    run = SyncRun(kind=kind, started_at=started_at, status="running", records=0, changes=0)
    session.add(run)
    await session.flush()
    return run


async def last_successful_sync(session: AsyncSession, kind: str) -> datetime | None:
    result: datetime | None = await session.scalar(
        select(func.max(SyncRun.ended_at)).where(
            SyncRun.kind == kind, SyncRun.status == "succeeded"
        )
    )
    return result


# ---- Seasons


async def list_seasons(session: AsyncSession) -> list[Season]:
    return list(await session.scalars(select(Season).order_by(Season.year)))


async def get_season(session: AsyncSession, year: int) -> Season | None:
    return await session.get(Season, year)


async def upsert_season(session: AsyncSession, year: int, **values: Any) -> None:
    stmt = insert(Season).values(year=year, **values)
    await session.execute(
        stmt.on_conflict_do_update(
            index_elements=[Season.year], set_={**values, "updated_at": func.now()}
        )
    )


@dataclass(frozen=True)
class SeasonEnd:
    """What `season.active_season` needs about a season's final game."""

    year: int
    final_game_at: datetime | None
    super_bowl_final: bool


async def season_ends(session: AsyncSession, fallback_days: int) -> list[SeasonEnd]:
    seasons = await list_seasons(session)
    ends: list[SeasonEnd] = []
    for season in seasons:
        final: Game | None = None
        if season.super_bowl_game_id is not None:
            final = await session.get(Game, season.super_bowl_game_id)
        final_at = final.sort_at if final else None
        if final is None:
            # Until the Super Bowl is listed, the season ends a while after its last known game,
            # never right after the conference championships.
            last = await session.scalar(
                select(Game)
                .where(Game.season == season.year)
                .order_by(Game.sort_at.desc())
                .limit(1)
            )
            final_at = last.sort_at + timedelta(days=fallback_days) if last else None
        ends.append(
            SeasonEnd(
                year=season.year,
                final_game_at=final_at,
                super_bowl_final=(
                    season.super_bowl_game_id is not None
                    and final is not None
                    and final.status in ("final", "final_ot")
                ),
            )
        )
    return ends


async def season_weeks(session: AsyncSession, year: int) -> list[int]:
    rows = await session.scalars(
        select(Game.week).where(Game.season == year).distinct().order_by(Game.week)
    )
    return list(rows)


async def current_week(session: AsyncSession, year: int, since: datetime) -> int | None:
    """Week of the next game (from `since`), else the season's last week."""
    week: int | None = await session.scalar(
        select(Game.week)
        .where(Game.season == year, Game.sort_at >= since)
        .order_by(Game.sort_at)
        .limit(1)
    )
    if week is None:
        week = await session.scalar(select(func.max(Game.week)).where(Game.season == year))
    return week


# ---- Games (sync side)


async def games_for_season(session: AsyncSession, year: int) -> list[Game]:
    return list(await session.scalars(select(Game).where(Game.season == year)))


async def upsert_game(session: AsyncSession, values: dict[str, Any]) -> uuid.UUID:
    stmt = insert(Game).values(**values)
    update = {k: stmt.excluded[k] for k in values if k != "apisports_game_id"}
    game_id: uuid.UUID | None = await session.scalar(
        stmt.on_conflict_do_update(
            index_elements=[Game.apisports_game_id], set_={**update, "updated_at": func.now()}
        ).returning(Game.id)
    )
    assert game_id is not None
    return game_id


async def delete_games(session: AsyncSession, ids: Sequence[uuid.UUID]) -> None:
    if ids:
        await session.execute(delete(Game).where(Game.id.in_(ids)))


async def add_changes(session: AsyncSession, rows: Sequence[dict[str, Any]]) -> None:
    for row in rows:
        session.add(GameChange(**row))


async def replace_schedule_tags(
    session: AsyncSession, game_ids: Sequence[uuid.UUID], rows: Sequence[dict[str, Any]]
) -> None:
    if game_ids:
        await session.execute(
            delete(GameTag).where(GameTag.game_id.in_(game_ids), GameTag.source == "schedule")
        )
    for row in rows:
        session.add(GameTag(source="schedule", **row))


# ---- Games (read side)


@dataclass(frozen=True)
class GameFilters:
    season: int
    week: int | None = None
    team: str | None = None
    from_: datetime | None = None
    to: datetime | None = None
    favorites_of: uuid.UUID | None = None  # the caller's user ID


@dataclass(frozen=True)
class Cursor:
    sort_at: datetime
    id: uuid.UUID


def _filtered(filters: GameFilters) -> Select[Game]:
    query = select(Game).where(Game.season == filters.season)
    if filters.week is not None:
        query = query.where(Game.week == filters.week)
    if filters.team is not None:
        query = query.where(
            or_(Game.home_team_id == filters.team, Game.away_team_id == filters.team)
        )
    if filters.from_ is not None:
        query = query.where(Game.sort_at >= filters.from_)
    if filters.to is not None:
        query = query.where(Game.sort_at <= filters.to)
    if filters.favorites_of is not None:
        favorites = select(UserFavoriteTeam.team_id).where(
            UserFavoriteTeam.user_id == filters.favorites_of
        )
        query = query.where(or_(Game.home_team_id.in_(favorites), Game.away_team_id.in_(favorites)))
    return query


async def list_games(
    session: AsyncSession, filters: GameFilters, cursor: Cursor | None, limit: int
) -> list[Game]:
    """Keyset page ordered by (sort_at, id); returns up to `limit + 1` rows to detect more."""
    query = _filtered(filters)
    if cursor is not None:
        query = query.where(tuple_(Game.sort_at, Game.id) > tuple_(cursor.sort_at, cursor.id))
    query = query.order_by(Game.sort_at, Game.id).limit(limit + 1)
    return list(await session.scalars(query))


async def get_game(session: AsyncSession, game_id: uuid.UUID) -> Game | None:
    return await session.get(Game, game_id)


async def tags_for(
    session: AsyncSession, game_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[GameTag]]:
    result: dict[uuid.UUID, list[GameTag]] = {gid: [] for gid in game_ids}
    if game_ids:
        rows = await session.scalars(
            select(GameTag).where(GameTag.game_id.in_(game_ids)).order_by(GameTag.tag)
        )
        for tag in rows:
            result[tag.game_id].append(tag)
    return result


async def venues_for(
    session: AsyncSession, venue_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, VenueRef]:
    if not venue_ids:
        return {}
    rows = await session.scalars(select(VenueRef).where(VenueRef.id.in_(venue_ids)))
    return {v.id: v for v in rows}
