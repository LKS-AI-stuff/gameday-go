from dataclasses import replace
from datetime import UTC, date, datetime

from app.domain.schedule_diff import Change, GameSnapshot, diff_games

BASE = GameSnapshot(
    provider_game_id="1",
    kickoff_at=datetime(2026, 11, 8, 18, 0, tzinfo=UTC),
    kickoff_tbd=False,
    game_date=date(2026, 11, 8),
    status="scheduled",
    venue_name="Soldier Field",
    venue_city="Chicago",
    home_team_id="CHI",
    away_team_id="GB",
)


def test_unchanged_game_has_no_changes() -> None:
    assert diff_games({"1": BASE}, [BASE]) == []


def test_each_changed_field_is_reported() -> None:
    moved = replace(BASE, kickoff_at=datetime(2026, 11, 9, 1, 20, tzinfo=UTC), status="postponed")
    assert diff_games({"1": BASE}, [moved]) == [
        Change("1", "kickoff_at", "2026-11-08T18:00:00+00:00", "2026-11-09T01:20:00+00:00"),
        Change("1", "status", "scheduled", "postponed"),
    ]


def test_tbd_flag_and_team_resolution() -> None:
    tbd = replace(BASE, kickoff_tbd=True, home_team_id=None)
    resolved = replace(BASE, kickoff_tbd=False)
    assert diff_games({"1": tbd}, [resolved]) == [
        Change("1", "kickoff_tbd", "true", "false"),
        Change("1", "home_team_id", None, "CHI"),
    ]


def test_new_and_missing_games_are_not_changes() -> None:
    assert diff_games({}, [BASE]) == []
    assert diff_games({"1": BASE}, []) == []
