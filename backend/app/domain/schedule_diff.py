"""Schedule change detection (FR-O2). Pure functions."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from datetime import date, datetime


@dataclass(frozen=True)
class GameSnapshot:
    """The fields of a game whose changes are recorded (and, from M5, alerted)."""

    provider_game_id: str
    kickoff_at: datetime | None
    kickoff_tbd: bool
    game_date: date | None
    status: str
    venue_name: str | None
    venue_city: str | None
    home_team_id: str | None
    away_team_id: str | None


@dataclass(frozen=True)
class Change:
    provider_game_id: str
    field: str
    old: str | None
    new: str | None


DIFFED_FIELDS = tuple(f.name for f in fields(GameSnapshot) if f.name != "provider_game_id")


def _render(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime | date):
        return value.isoformat()
    return str(value).lower() if isinstance(value, bool) else str(value)


def diff_games(
    stored: Mapping[str, GameSnapshot], incoming: Sequence[GameSnapshot]
) -> list[Change]:
    """One change per changed field. New games aren't changes; missing ones are the caller's."""
    changes: list[Change] = []
    for new in incoming:
        old = stored.get(new.provider_game_id)
        if old is None:
            continue
        for name in DIFFED_FIELDS:
            before, after = getattr(old, name), getattr(new, name)
            if before != after:
                changes.append(Change(new.provider_game_id, name, _render(before), _render(after)))
    return changes
