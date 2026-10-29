"""Season rollover (BR-W2, FR-O1c). Pure functions."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class SeasonInfo:
    year: int
    # Super Bowl kickoff, or the season's last known game time before it's scheduled.
    final_game_at: datetime | None
    super_bowl_final: bool


def season_over(season: SeasonInfo, now: datetime) -> bool:
    """Over once the Super Bowl is final, or one day after it was scheduled."""
    if season.super_bowl_final:
        return True
    return season.final_game_at is not None and now >= season.final_game_at + timedelta(days=1)


def default_season(now: datetime) -> int:
    """With nothing known yet: the season starting this year from March, else last year's."""
    return now.year if now.month >= 3 else now.year - 1


def active_season(now: datetime, seasons: Sequence[SeasonInfo]) -> int:
    if not seasons:
        return default_season(now)
    for season in sorted(seasons, key=lambda s: s.year):
        if not season_over(season, now):
            return season.year
    return max(s.year for s in seasons) + 1
