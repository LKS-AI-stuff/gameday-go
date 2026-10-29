"""Schedule sync (TDD §10.2 `schedule_sync`; FR-O1, FR-O1c, FR-O2, FR-LS10).

Runs from `cli sync-schedule` in M1 and from the worker's daily job in M4. Provider calls
happen outside any open transaction (TDD §5.3); each season's results are applied in one.
"""

import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.budgets import BudgetExhausted
from app.core.http import ProviderDisabled
from app.core.logging import get_logger
from app.core.settings import Settings
from app.db.models import Game, Team
from app.db.repositories import reference, schedule
from app.domain import season as season_rules
from app.domain import significance
from app.domain.models import SUPER_BOWL_WEEK, GameFacts, ProviderGame, TeamFacts
from app.domain.schedule_diff import GameSnapshot, diff_games
from app.modules.schedule.reference import Overrides, ReferenceDataError, load_overrides
from app.providers.apisports.base import ScheduleProvider
from app.providers.errors import ProviderError

log = get_logger(__name__)

EASTERN = ZoneInfo("America/New_York")
TBD_SORT_TIME = time(23, 59)
TBD_TEAM = "TBD"


@dataclass(frozen=True)
class SyncResult:
    run_id: uuid.UUID
    status: str
    seasons: tuple[int, ...]
    records: int
    changes: int
    error: str | None = None


def sort_at(game: ProviderGame) -> datetime | None:
    if game.kickoff_at is not None:
        return game.kickoff_at
    if game.game_date is not None:
        return datetime.combine(game.game_date, TBD_SORT_TIME, tzinfo=EASTERN)
    return None


def _snapshot(provider_id: str, values: dict[str, Any]) -> GameSnapshot:
    return GameSnapshot(
        provider_game_id=provider_id,
        kickoff_at=values["kickoff_at"],
        kickoff_tbd=values["kickoff_tbd"],
        game_date=values["game_date"],
        status=values["status"],
        venue_name=values["venue_name"],
        venue_city=values["venue_city"],
        home_team_id=values["home_team_id"],
        away_team_id=values["away_team_id"],
    )


def _stored_snapshot(game: Game) -> GameSnapshot:
    return GameSnapshot(
        provider_game_id=game.apisports_game_id,
        kickoff_at=game.kickoff_at,
        kickoff_tbd=game.kickoff_tbd,
        game_date=game.game_date,
        status=game.status,
        venue_name=game.venue_name,
        venue_city=game.venue_city,
        home_team_id=game.home_team_id,
        away_team_id=game.away_team_id,
    )


class _Venues:
    """Resolves (name, city) to a `venues_ref` row with coordinates where known."""

    def __init__(self, session: AsyncSession, overrides: Overrides) -> None:
        self._session = session
        self._overrides = overrides
        self._cache: dict[tuple[str, str | None], tuple[uuid.UUID, str | None, str | None]] = {}
        self.unmapped: set[str] = set()

    async def resolve(
        self, name: str | None, city: str | None
    ) -> tuple[uuid.UUID | None, str | None, str | None]:
        """(venue_id, state, country); unknown parts are None (distance unknown, FR-O1a)."""
        if not name:
            return None, None, None
        key = (name, city)
        if key in self._cache:
            return self._cache[key]
        entry = self._overrides.venue_cities.get(city or "")
        state = country = None
        lat = lng = None
        source = "none"
        if entry is None:
            if city:
                self.unmapped.add(city)
        else:
            state, country = entry.state, entry.country
            lat, lng = entry.lat, entry.lng
            source = "override" if lat is not None else "none"
            if lat is None and city and state:
                place = await reference.get_place(self._session, city, state)
                if place is not None:
                    lat, lng, source = place.lat, place.lng, "place_centroids"
        venue = await reference.upsert_venue(
            self._session,
            {
                "name": name,
                "city": city,
                "state": state,
                "country": country,
                "lat": lat,
                "lng": lng,
                "source": source,
            },
        )
        self._cache[key] = (venue.id, state, country)
        return self._cache[key]


async def _apply_season(
    session: AsyncSession,
    year: int,
    incoming: list[ProviderGame],
    run_id: uuid.UUID,
    now: datetime,
    settings: Settings,
    overrides: Overrides,
) -> tuple[int, int]:
    teams = {t.apisports_team_id: t for t in await reference.list_teams(session)}
    if not teams:
        raise ReferenceDataError("No teams yet: run `uv run python -m app.cli seed` first")
    venues = _Venues(session, overrides)
    stored = {g.apisports_game_id: g for g in await schedule.games_for_season(session, year)}

    rows: dict[str, dict[str, Any]] = {}
    for game in incoming:
        home = teams.get(game.home.provider_team_id) if game.home else None
        away = teams.get(game.away.provider_team_id) if game.away else None
        if (game.home and home is None) or (game.away and away is None):
            # Never attach a record to the wrong game (FR-LS10, AC-36).
            log.warning("apisports_game_unmapped", game=game.provider_game_id)
            continue
        order = sort_at(game)
        if order is None:
            log.warning("apisports_game_undated", game=game.provider_game_id)
            continue
        venue_id, venue_state, venue_country = await venues.resolve(
            game.venue_name, game.venue_city
        )
        rows[game.provider_game_id] = {
            "apisports_game_id": game.provider_game_id,
            "season": year,
            "week": game.week,
            "stage": game.stage,
            "home_team_id": home.id if home else None,
            "away_team_id": away.id if away else None,
            "home_placeholder": None if home else TBD_TEAM,
            "away_placeholder": None if away else TBD_TEAM,
            "game_date": game.game_date,
            "kickoff_at": game.kickoff_at,
            "kickoff_tbd": game.kickoff_tbd,
            "sort_at": order,
            "venue_id": venue_id,
            "venue_name": game.venue_name,
            "venue_city": game.venue_city,
            "venue_state": venue_state,
            "venue_country": venue_country,
            "status": game.status.value,
            "last_synced_at": now,
        }
    if venues.unmapped:
        log.warning("venue_cities_unmapped", cities=sorted(venues.unmapped))

    changes = diff_games(
        {pid: _stored_snapshot(g) for pid, g in stored.items()},
        [_snapshot(pid, values) for pid, values in rows.items()],
    )
    ids = {pid: await schedule.upsert_game(session, values) for pid, values in rows.items()}
    await schedule.add_changes(
        session,
        [
            {
                "game_id": ids[c.provider_game_id],
                "field": c.field,
                "old_value": c.old,
                "new_value": c.new,
                "detected_at": now,
                "sync_run_id": run_id,
            }
            for c in changes
        ],
    )

    missing = [g for pid, g in stored.items() if pid not in rows]
    # Undecided playoff slots are re-listed under new IDs once teams are known.
    placeholders = [g.id for g in missing if g.home_team_id is None and g.away_team_id is None]
    await schedule.delete_games(session, placeholders)
    if len(missing) > len(placeholders):
        log.warning(
            "apisports_games_missing",
            games=[g.apisports_game_id for g in missing if g.id not in placeholders],
        )

    await _recompute_tags(session, year, list(teams.values()), rows, ids, now, settings)
    await _update_home_venues(session, list(teams.values()), rows)

    super_bowl = next((ids[pid] for pid, v in rows.items() if v["week"] == SUPER_BOWL_WEEK), None)
    existing = await schedule.get_season(session, year)
    if rows:
        await schedule.upsert_season(
            session,
            year,
            status="completed" if existing and existing.status == "completed" else "active",
            schedule_available_at=(
                existing.schedule_available_at
                if existing and existing.schedule_available_at
                else now
            ),
            super_bowl_game_id=super_bowl,
        )
    elif existing is None:
        await schedule.upsert_season(session, year, status="upcoming")
    return len(rows), len(changes)


async def _recompute_tags(
    session: AsyncSession,
    year: int,
    teams: list[Team],
    rows: dict[str, dict[str, Any]],
    ids: dict[str, uuid.UUID],
    now: datetime,
    settings: Settings,
) -> None:
    facts = [
        GameFacts(
            id=ids[pid],
            season=year,
            week=v["week"],
            stage=v["stage"],
            home_team_id=v["home_team_id"],
            away_team_id=v["away_team_id"],
            game_date=v["game_date"],
            kickoff_at=v["kickoff_at"],
            venue_country=v["venue_country"],
        )
        for pid, v in rows.items()
    ]
    team_facts = {t.id: TeamFacts(t.id, t.conference, t.division) for t in teams}
    rivalries = {
        significance.rivalry_key(r.team_a, r.team_b): r.reason
        for r in await reference.rivalries(session)
    }
    tags = significance.schedule_tags(facts, team_facts, rivalries, settings.primetime_start_et)
    await schedule.replace_schedule_tags(
        session,
        list(ids.values()),
        [
            {
                "game_id": game_id,
                "tag": t.tag,
                "weight": t.weight,
                "detail": t.detail,
                "computed_at": now,
            }
            for game_id, game_tags in tags.items()
            for t in game_tags
        ],
    )


async def _update_home_venues(
    session: AsyncSession, teams: list[Team], rows: dict[str, dict[str, Any]]
) -> None:
    """Each team's home venue is where it plays most regular-season home games in the US."""
    counts: dict[str, Counter[uuid.UUID]] = {}
    for v in rows.values():
        if (
            v["stage"] == "regular"
            and v["home_team_id"]
            and v["venue_id"]
            and v["venue_country"] == "US"
        ):
            counts.setdefault(v["home_team_id"], Counter())[v["venue_id"]] += 1
    venue_ids = [c.most_common(1)[0][0] for c in counts.values()]
    venues = await schedule.venues_for(session, venue_ids)
    for team in teams:
        if team.id not in counts:
            continue
        venue = venues[counts[team.id].most_common(1)[0][0]]
        await reference.update_team(
            session,
            team.id,
            {
                "home_venue_name": venue.name,
                "home_venue_lat": venue.lat,
                "home_venue_lng": venue.lng,
                "state": team.state or venue.state,
            },
        )


async def _season_year(session: AsyncSession, now: datetime, settings: Settings) -> int:
    ends = await schedule.season_ends(session, settings.season_end_fallback_days)
    return season_rules.active_season(
        now,
        [season_rules.SeasonInfo(e.year, e.final_game_at, e.super_bowl_final) for e in ends],
    )


async def schedule_sync(
    sessionmaker: async_sessionmaker[AsyncSession],
    provider: ScheduleProvider,
    settings: Settings,
    now: datetime | None = None,
    season: int | None = None,
) -> SyncResult:
    now = now or datetime.now(UTC)
    overrides = load_overrides()
    async with sessionmaker() as session:
        run = await schedule.start_sync_run(session, "schedule", now)
        run_id = run.id
        await session.commit()

    records = changes = 0
    synced: list[int] = []
    error: str | None = None
    try:
        async with sessionmaker() as session:
            year = season or await _season_year(session, now, settings)
        for _ in range(2):  # the active season, then the next one if it just ended (BR-W2)
            incoming = await provider.games_for_season(year)
            async with sessionmaker() as session:
                count, changed = await _apply_season(
                    session, year, incoming, run_id, now, settings, overrides
                )
                await session.commit()
            records, changes = records + count, changes + changed
            synced.append(year)
            if season is not None:
                break
            async with sessionmaker() as session:
                next_year = await _season_year(session, now, settings)
                if next_year == year:
                    break
                await schedule.upsert_season(session, year, status="completed")
                await session.commit()
            year = next_year
    except (ProviderDisabled, BudgetExhausted, ProviderError, ReferenceDataError) as exc:
        # Expected failures: stored games stay as they were (NFR-11).
        error = type(exc).__name__
        log.warning("schedule_sync_failed", error=error, detail=str(exc))
    except Exception as exc:
        error = type(exc).__name__
        log.exception("schedule_sync_failed", error=error)

    async with sessionmaker() as session:
        sync_run = await session.get(type(run), run_id)
        assert sync_run is not None
        sync_run.season = synced[-1] if synced else None
        sync_run.ended_at = datetime.now(UTC)
        sync_run.status = "failed" if error else "succeeded"
        sync_run.records = records
        sync_run.changes = changes
        sync_run.error = error
        await session.commit()
    log.info(
        "schedule_sync_finished",
        status="failed" if error else "succeeded",
        seasons=synced,
        records=records,
        changes=changes,
    )
    return SyncResult(
        run_id, "failed" if error else "succeeded", tuple(synced), records, changes, error
    )
