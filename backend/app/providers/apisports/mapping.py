"""API-Sports American Football payloads → normalized types (TDD §8.3).

Shapes confirmed against recorded 2026 responses (T4, `tests/contract/fixtures/apisports/`):
- times come as a UTC `timestamp`. TBD kickoffs (flex weeks, playoffs) are listed at "00:00"
  with `date` as the game day; since 00:00 UTC is also a real 8 PM EDT kickoff, a regular-season
  game counts as TBD only when several games share "00:00" on that date;
- the Super Bowl was listed as "Pro Bowl" (SoFi Stadium, Feb 14, 2027): the last postseason
  entry after the conference championships is taken as the Super Bowl unless one is named;
- venues have a name and city only (no state or country);
- undecided playoff teams have `id` 0 and no name;
- stages are "Pre Season" (dropped, BR-W3), "Regular Season" and "Post Season".
"""

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.core.logging import get_logger
from app.domain.models import (
    CONFERENCE_WEEK,
    DIVISIONAL_WEEK,
    SUPER_BOWL_WEEK,
    WILD_CARD_WEEK,
    GameStatus,
    Provenance,
    ProviderGame,
    ProviderStanding,
    ProviderTeam,
    ProviderTeamRef,
    Stage,
)

log = get_logger(__name__)

EASTERN = ZoneInfo("America/New_York")
TBD_TIME = "00:00"

STAGES: Mapping[str, Stage] = {"Regular Season": "regular", "Post Season": "playoff"}
PLAYOFF_WEEKS: Mapping[str, int] = {
    "Wild Card": WILD_CARD_WEEK,
    "Divisional Round": DIVISIONAL_WEEK,
    "Conference Championships": CONFERENCE_WEEK,
    "Super Bowl": SUPER_BOWL_WEEK,
}
# Postseason entries that aren't NFL games for planning purposes.
PRO_BOWL = "Pro Bowl"
SKIPPED_WEEKS = frozenset({PRO_BOWL})
# A date with at least this many regular-season games at "00:00" is a block of TBD kickoffs.
TBD_DATE_MIN_GAMES = 2
STATUSES: Mapping[str, GameStatus] = {
    "NS": GameStatus.SCHEDULED,
    "Q1": GameStatus.IN_PROGRESS,
    "Q2": GameStatus.IN_PROGRESS,
    "Q3": GameStatus.IN_PROGRESS,
    "Q4": GameStatus.IN_PROGRESS,
    "OT": GameStatus.IN_PROGRESS,
    "HT": GameStatus.HALFTIME,
    "FT": GameStatus.FINAL,
    "AOT": GameStatus.FINAL_OT,
    "PST": GameStatus.POSTPONED,
    "CANC": GameStatus.CANCELLED,
}
_WEEK = re.compile(r"^Week (\d{1,2})$")
CONFERENCES = {"American Football Conference": "AFC", "National Football Conference": "NFC"}


def provider_errors(payload: Mapping[str, Any]) -> bool:
    """API-Sports reports plan and parameter errors in the body with HTTP 200."""
    return bool(payload.get("errors"))


def _week(stage: Stage, raw: str | None) -> int | None:
    if raw is None:
        return None
    if stage == "regular":
        match = _WEEK.match(raw)
        return int(match.group(1)) if match else None
    return PLAYOFF_WEEKS.get(raw)


def _team(raw: Mapping[str, Any] | None) -> ProviderTeamRef | None:
    if not raw or not raw.get("id") or not raw.get("name"):
        return None
    return ProviderTeamRef(provider_team_id=str(raw["id"]), name=str(raw["name"]))


def tbd_dates(items: Sequence[Mapping[str, Any]]) -> set[str]:
    """Dates whose "00:00" regular-season kickoffs are TBD rather than 8 PM EDT games."""
    counts = Counter(
        i["game"]["date"]["date"]
        for i in items
        if i["game"].get("stage") == "Regular Season"
        and (i["game"].get("date") or {}).get("time") == TBD_TIME
    )
    return {day for day, n in counts.items() if n >= TBD_DATE_MIN_GAMES}


def mislabeled_super_bowl(items: Sequence[Mapping[str, Any]]) -> str | None:
    """ID of a "Pro Bowl" entry that is really the Super Bowl (the season's last game)."""
    post = [i["game"] for i in items if i["game"].get("stage") == "Post Season"]
    if any(g.get("week") == "Super Bowl" for g in post):
        return None
    last = max(post, key=lambda g: (g.get("date") or {}).get("timestamp") or 0, default=None)
    if last is None or last.get("week") != PRO_BOWL:
        return None
    rounds = [g for g in post if g.get("week") in PLAYOFF_WEEKS]
    last_round = max(((g.get("date") or {}).get("timestamp") or 0 for g in rounds), default=0)
    return str(last["id"]) if (last.get("date") or {}).get("timestamp", 0) > last_round else None


def map_game(
    item: Mapping[str, Any],
    season: int,
    retrieved_at: datetime,
    *,
    tbd_on: set[str] | None = None,
    super_bowl_id: str | None = None,
) -> ProviderGame | None:
    """None for games the app doesn't show (preseason, Pro Bowl) or can't interpret.

    `tbd_on` and `super_bowl_id` come from the whole response (`map_games`); without them,
    every "00:00" kickoff counts as TBD.
    """
    game = item["game"]
    provider_id = str(game["id"])
    raw_stage, raw_week = game.get("stage"), game.get("week")
    if provider_id == super_bowl_id:
        raw_week = "Super Bowl"
    if raw_stage == "Pre Season" or raw_week in SKIPPED_WEEKS:
        return None
    stage = STAGES.get(raw_stage or "")
    week = _week(stage, raw_week) if stage else None
    if stage is None or week is None:
        log.warning("apisports_stage_unmapped", game=provider_id, stage=raw_stage, week=raw_week)
        return None

    when = game.get("date") or {}
    timestamp = when.get("timestamp")
    at_midnight = when.get("time") == TBD_TIME
    if stage == "regular" and tbd_on is not None:
        at_midnight = at_midnight and when.get("date") in tbd_on
    tbd = at_midnight or timestamp is None
    kickoff_at = None if tbd or timestamp is None else datetime.fromtimestamp(int(timestamp), UTC)
    if kickoff_at is not None:
        game_date: date | None = kickoff_at.astimezone(EASTERN).date()
    else:
        game_date = date.fromisoformat(when["date"]) if when.get("date") else None

    short = (game.get("status") or {}).get("short")
    status = STATUSES.get(short or "")
    if status is None:
        started = kickoff_at is not None and kickoff_at <= retrieved_at
        log.warning("apisports_status_unmapped", game=provider_id, status=short)
        if started:
            return None
        status = GameStatus.SCHEDULED

    teams = item.get("teams") or {}
    venue = game.get("venue") or {}
    return ProviderGame(
        provider_game_id=provider_id,
        season=season,
        week=week,
        stage=stage,
        game_date=game_date,
        kickoff_at=kickoff_at,
        kickoff_tbd=tbd,
        home=_team(teams.get("home")),
        away=_team(teams.get("away")),
        venue_name=venue.get("name"),
        venue_city=venue.get("city"),
        status=status,
        provenance=Provenance(provider="apisports", retrieved_at=retrieved_at),
    )


def map_games(
    payload: Mapping[str, Any], season: int, retrieved_at: datetime
) -> list[ProviderGame]:
    items = payload.get("response", [])
    tbd_on, super_bowl_id = tbd_dates(items), mislabeled_super_bowl(items)
    games = (
        map_game(item, season, retrieved_at, tbd_on=tbd_on, super_bowl_id=super_bowl_id)
        for item in items
    )
    return [g for g in games if g is not None]


def map_teams(payload: Mapping[str, Any]) -> list[ProviderTeam]:
    return [
        ProviderTeam(provider_team_id=str(t["id"]), code=t["code"], name=t["name"], city=t["city"])
        for t in payload.get("response", [])
        if t.get("id") and t.get("code") and t.get("name") and t.get("city")
    ]


def map_standings(payload: Mapping[str, Any]) -> list[ProviderStanding]:
    standings: list[ProviderStanding] = []
    for row in payload.get("response", []):
        conference = CONFERENCES.get(row.get("conference") or "")
        division = (row.get("division") or "").split(" ")[-1]
        if conference and division in {"East", "North", "South", "West"}:
            standings.append(
                ProviderStanding(
                    provider_team_id=str(row["team"]["id"]),
                    conference=conference,
                    division=division,
                )
            )
    return standings
