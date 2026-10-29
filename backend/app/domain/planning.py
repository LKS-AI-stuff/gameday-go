"""Planning window (BR-W1, FR-SC8). Pure functions."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.domain.models import FINISHED_STATUSES, GameStatus

EASTERN = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class Open:
    pass


@dataclass(frozen=True)
class OpensOn:
    at: datetime  # UTC; clients show its date in the user's time zone


@dataclass(frozen=True)
class Closed:
    pass


type PlanningStatus = Open | OpensOn | Closed


def reference_time(kickoff_at: datetime | None, game_date: date | None) -> datetime | None:
    """Kickoff, or the start of the game day (Eastern) when the time is TBD."""
    if kickoff_at is not None:
        return kickoff_at
    if game_date is not None:
        return datetime.combine(game_date, time(0, 0), tzinfo=EASTERN)
    return None


def planning_status(
    kickoff_at: datetime | None,
    game_date: date | None,
    status: GameStatus,
    now: datetime,
    window_days: int,
) -> PlanningStatus:
    ref = reference_time(kickoff_at, game_date)
    if ref is None or ref <= now or status in FINISHED_STATUSES:
        return Closed()
    opens_at = ref - timedelta(days=window_days)
    if opens_at <= now:
        return Open()
    return OpensOn(at=opens_at.astimezone(UTC))  # times leave the backend in UTC (NFR-4)
