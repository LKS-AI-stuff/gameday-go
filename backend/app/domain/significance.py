"""Game significance tags (BRD §7.6). Pure functions.

Schedule-based tags only; record-based tags (`record_tags`) arrive with standings in M4.
"""

import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.domain.models import GameFacts, Tag, TeamFacts

EASTERN = ZoneInfo("America/New_York")
US = "US"
# Thursday, Sunday and Monday nights (datetime.weekday()).
PRIMETIME_WEEKDAYS = frozenset({3, 6, 0})

PLAYOFF = "playoff"
DIVISION_RIVALRY = "division_rivalry"
FEATURED_RIVALRY = "featured_rivalry"
PRIMETIME = "primetime"
HOME_OPENER = "home_opener"
HOME_FINALE = "home_finale"
INTERNATIONAL = "international"


def rivalry_key(team_a: str, team_b: str) -> frozenset[str]:
    """Unordered pair: a featured rivalry applies whichever team is home."""
    return frozenset((team_a, team_b))


def is_international(venue_country: str | None) -> bool:
    return venue_country is not None and venue_country != US


def is_primetime(kickoff_at: datetime | None, start_et: time) -> bool:
    if kickoff_at is None:
        return False
    local = kickoff_at.astimezone(EASTERN)
    return local.weekday() in PRIMETIME_WEEKDAYS and local.time() >= start_et


def _sort_key(game: GameFacts) -> tuple[str, str]:
    when = game.kickoff_at.isoformat() if game.kickoff_at else ""
    return (game.game_date.isoformat() if game.game_date else "", when)


def home_bookends(games: Sequence[GameFacts]) -> tuple[set[uuid.UUID], set[uuid.UUID]]:
    """Each home team's first and last regular-season home game, international excluded."""
    by_team: dict[str, list[GameFacts]] = {}
    for game in games:
        if (
            game.stage == "regular"
            and game.home_team_id is not None
            and not is_international(game.venue_country)
        ):
            by_team.setdefault(game.home_team_id, []).append(game)
    openers: set[uuid.UUID] = set()
    finales: set[uuid.UUID] = set()
    for home_games in by_team.values():
        ordered = sorted(home_games, key=_sort_key)
        openers.add(ordered[0].id)
        finales.add(ordered[-1].id)
    return openers, finales


def schedule_tags(
    games: Sequence[GameFacts],
    teams: Mapping[str, TeamFacts],
    rivalries: Mapping[frozenset[str], str],
    primetime_start_et: time,
) -> dict[uuid.UUID, list[Tag]]:
    """Tags for one season's games. Whole-season input: opener and finale need the schedule."""
    openers, finales = home_bookends(games)
    result: dict[uuid.UUID, list[Tag]] = {}
    for game in games:
        tags: list[Tag] = []
        if game.stage == "playoff":
            tags.append(Tag(PLAYOFF, "high"))
        home = teams.get(game.home_team_id) if game.home_team_id else None
        away = teams.get(game.away_team_id) if game.away_team_id else None
        if home is not None and away is not None:
            if home.conference == away.conference and home.division == away.division:
                tags.append(Tag(DIVISION_RIVALRY, "high"))
            reason = rivalries.get(rivalry_key(home.id, away.id))
            if reason is not None:
                tags.append(Tag(FEATURED_RIVALRY, "high", reason))
            if is_primetime(game.kickoff_at, primetime_start_et):
                tags.append(Tag(PRIMETIME, "medium"))
            if game.id in openers:
                tags.append(Tag(HOME_OPENER, "medium"))
            if game.id in finales:
                tags.append(Tag(HOME_FINALE, "medium"))
            if is_international(game.venue_country):
                tags.append(Tag(INTERNATIONAL, "info"))
        result[game.id] = tags
    return result
