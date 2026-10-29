"""Teams, season and games for browsing (BRD §8.3; FR-SC1-SC5, FR-SC8, FR-O1c)."""

import base64
import binascii
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ProblemError
from app.core.settings import Settings
from app.db.models import Game, Team, User
from app.db.repositories import preferences as preferences_repo
from app.db.repositories import reference, schedule
from app.domain import geo
from app.domain.models import (
    CONFERENCE_WEEK,
    DIVISIONAL_WEEK,
    SUPER_BOWL_WEEK,
    WILD_CARD_WEEK,
    GameStatus,
    LatLng,
)
from app.domain.planning import Closed, Open, OpensOn, planning_status
from app.domain.season import SeasonInfo, active_season
from app.modules.schedule import schemas

WEEK_LABELS = {
    WILD_CARD_WEEK: "WILD CARD",
    DIVISIONAL_WEEK: "DIVISIONAL",
    CONFERENCE_WEEK: "CONF. CHAMPIONSHIPS",
    SUPER_BOWL_WEEK: "SUPER BOWL",
}
# "Current week" keeps showing a week until half a day after its last game starts.
CURRENT_WEEK_GRACE = timedelta(hours=12)
MAX_PAGE = 100


def week_label(week: int) -> str:
    return WEEK_LABELS.get(week, f"WEEK {week}")


def _invalid_cursor() -> ProblemError:
    return ProblemError(422, "invalid_cursor", "Invalid cursor")


def encode_cursor(game: Game) -> str:
    raw = json.dumps({"s": game.sort_at.isoformat(), "i": str(game.id)})
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(value: str) -> schedule.Cursor:
    try:
        data = json.loads(base64.urlsafe_b64decode(value.encode()))
        return schedule.Cursor(datetime.fromisoformat(data["s"]), uuid.UUID(data["i"]))
    except (ValueError, KeyError, TypeError, binascii.Error) as exc:
        raise _invalid_cursor() from exc


async def active_year(session: AsyncSession, settings: Settings, now: datetime) -> int:
    ends = await schedule.season_ends(session, settings.season_end_fallback_days)
    return active_season(
        now, [SeasonInfo(e.year, e.final_game_at, e.super_bowl_final) for e in ends]
    )


async def list_teams(session: AsyncSession) -> list[schemas.Team]:
    return [
        schemas.Team(
            id=t.id,
            name=t.name,
            nickname=t.nickname,
            city=t.city,
            conference=t.conference,
            division=t.division,
        )
        for t in await reference.list_teams(session)
    ]


async def get_season(session: AsyncSession, settings: Settings, now: datetime) -> schemas.Season:
    year = await active_year(session, settings, now)
    row = await schedule.get_season(session, year)
    available = row is not None and row.schedule_available_at is not None
    weeks = await schedule.season_weeks(session, year) if available else []
    return schemas.Season(
        year=year,
        status=row.status if row else "upcoming",
        schedule_available=available,
        current_week=(
            await schedule.current_week(session, year, now - CURRENT_WEEK_GRACE)
            if available
            else None
        ),
        weeks=[schemas.WeekOption(week=w, label=week_label(w)) for w in weeks],
        planning_window_days=settings.planning_window_days,
        schedule_updated_at=await schedule.last_successful_sync(session, "schedule"),
    )


@dataclass(frozen=True)
class _Viewer:
    home: LatLng | None
    travel: str | None
    favorites: frozenset[str]


async def _viewer(session: AsyncSession, user: User) -> _Viewer:
    prefs = await preferences_repo.get(session, user.id)
    if prefs is None:
        return _Viewer(None, None, frozenset())
    zip_row = await reference.get_zip(session, prefs.home_zip)
    return _Viewer(
        LatLng(zip_row.lat, zip_row.lng) if zip_row else None,
        prefs.travel,
        frozenset(await preferences_repo.favorite_team_ids(session, user.id)),
    )


def _team_ref(team: Team | None) -> schemas.TeamRef | None:
    return schemas.TeamRef(id=team.id, nickname=team.nickname, name=team.name) if team else None


def _planning(game: Game, now: datetime, window_days: int) -> schemas.Planning:
    result = planning_status(
        game.kickoff_at, game.game_date, GameStatus(game.status), now, window_days
    )
    if isinstance(result, Open):
        return schemas.Planning(status="open")
    if isinstance(result, OpensOn):
        return schemas.Planning(status="opens_on", opens_at=result.at)
    assert isinstance(result, Closed)
    return schemas.Planning(status="closed")


class _Builder:
    """Turns game rows into API objects with tags, distance and planning status."""

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        viewer: _Viewer,
        now: datetime,
    ) -> None:
        self._session = session
        self._settings = settings
        self._viewer = viewer
        self._now = now
        self._teams: dict[str, Team] = {}

    async def load(self, games: list[Game]) -> None:
        self._teams = {t.id: t for t in await reference.list_teams(self._session)}
        ids = [g.id for g in games]
        self._tags = await schedule.tags_for(self._session, ids)
        venue_ids = [g.venue_id for g in games if g.venue_id]
        self._venues = await schedule.venues_for(self._session, venue_ids)

    def distance(self, game: Game) -> float | None:
        venue = self._venues.get(game.venue_id) if game.venue_id else None
        if self._viewer.home is None or venue is None or venue.lat is None or venue.lng is None:
            return None
        return round(geo.haversine_miles(self._viewer.home, LatLng(venue.lat, venue.lng)), 1)

    def summary(self, game: Game) -> schemas.GameSummary:
        home = self._teams.get(game.home_team_id) if game.home_team_id else None
        away = self._teams.get(game.away_team_id) if game.away_team_id else None
        return schemas.GameSummary(
            id=game.id,
            season=game.season,
            week=game.week,
            week_label=week_label(game.week),
            stage=game.stage,
            game_date=game.game_date,
            kickoff_at=game.kickoff_at,
            kickoff_tbd=game.kickoff_tbd,
            home=_team_ref(home),
            away=_team_ref(away),
            home_placeholder=game.home_placeholder,
            away_placeholder=game.away_placeholder,
            venue_name=game.venue_name,
            venue_city=game.venue_city,
            venue_state=game.venue_state,
            venue_country=game.venue_country,
            status=game.status,
            tags=[
                schemas.GameTag(tag=t.tag, weight=t.weight, detail=t.detail)
                for t in self._tags.get(game.id, [])
            ],
            planning=_planning(game, self._now, self._settings.planning_window_days),
            distance_mi=self.distance(game),
            is_favorite=bool({game.home_team_id, game.away_team_id} & self._viewer.favorites),
            is_sample=game.is_sample,
        )

    def travel_hint(self, game: Game) -> str | None:
        """Shows the Low travel rule before planning (UI/UX §7.5); eligibility itself is M3's."""
        distance = self.distance(game)
        if self._viewer.travel != "low" or distance is None:
            return None
        return "outside_travel_area" if distance > self._settings.local_area_miles else None


async def list_games(
    session: AsyncSession,
    settings: Settings,
    user: User,
    now: datetime,
    *,
    season: int | None,
    week: int | None,
    team: str | None,
    favorites: bool,
    from_: datetime | None,
    to: datetime | None,
    cursor: str | None,
    limit: int,
) -> schemas.GamePage:
    for bound in (from_, to):
        if bound is not None and bound.tzinfo is None:
            # Times travel in UTC with an explicit offset (NFR-4).
            raise ProblemError(422, "naive_datetime", "from and to need a time zone, e.g. Z")
    filters = schedule.GameFilters(
        season=season or await active_year(session, settings, now),
        week=week,
        team=team,
        from_=from_,
        to=to,
        favorites_of=user.id if favorites else None,
    )
    rows = await schedule.list_games(
        session, filters, decode_cursor(cursor) if cursor else None, min(limit, MAX_PAGE)
    )
    page, more = rows[:limit], len(rows) > limit
    builder = _Builder(session, settings, await _viewer(session, user), now)
    await builder.load(page)
    return schemas.GamePage(
        items=[builder.summary(g) for g in page],
        next_cursor=encode_cursor(page[-1]) if more and page else None,
    )


async def get_game(
    session: AsyncSession, settings: Settings, user: User, game_id: uuid.UUID, now: datetime
) -> schemas.GameDetail:
    game = await schedule.get_game(session, game_id)
    if game is None:
        raise ProblemError(404, "not_found", "Game not found")
    builder = _Builder(session, settings, await _viewer(session, user), now)
    await builder.load([game])
    summary = builder.summary(game)
    return schemas.GameDetail(
        **summary.model_dump(),
        source=schemas.Source(
            schedule_updated_at=await schedule.last_successful_sync(session, "schedule"),
            game_synced_at=game.last_synced_at,
        ),
        travel_hint=builder.travel_hint(game),
    )


def utcnow() -> datetime:
    return datetime.now(UTC)
