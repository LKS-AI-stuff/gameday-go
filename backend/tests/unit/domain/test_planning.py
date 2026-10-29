from datetime import UTC, date, datetime, timedelta

from app.domain.models import GameStatus
from app.domain.planning import Closed, Open, OpensOn, PlanningStatus, planning_status

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)


def status(
    kickoff: datetime | None, game_date: date | None = None, s: str = "scheduled"
) -> PlanningStatus:
    return planning_status(kickoff, game_date, GameStatus(s), NOW, 30)


def test_exactly_30_days_is_open() -> None:
    assert status(NOW + timedelta(days=30)) == Open()


def test_one_second_past_30_days_opens_later() -> None:
    kickoff = NOW + timedelta(days=30, seconds=1)
    assert status(kickoff) == OpensOn(at=kickoff - timedelta(days=30))


def test_past_kickoff_is_closed() -> None:
    assert status(NOW - timedelta(minutes=1)) == Closed()


def test_final_and_cancelled_are_closed() -> None:
    assert status(NOW + timedelta(days=2), s="final") == Closed()
    assert status(NOW + timedelta(days=2), s="cancelled") == Closed()


def test_postponed_future_game_stays_open() -> None:
    assert status(NOW + timedelta(days=2), s="postponed") == Open()


def test_tbd_time_uses_game_date_start_eastern() -> None:
    # Jan 10, 2027 00:00 ET is 05:00 UTC; the window opens 30 days earlier.
    result = status(None, date(2027, 1, 10))
    assert result == OpensOn(at=datetime(2026, 12, 11, 5, 0, tzinfo=UTC))
    assert isinstance(result, OpensOn) and result.at.utcoffset() == timedelta(0)


def test_unknown_date_is_closed() -> None:
    assert status(None, None) == Closed()
