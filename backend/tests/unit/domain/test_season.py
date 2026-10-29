from datetime import UTC, datetime

from app.domain.season import SeasonInfo, active_season

SB_2026 = datetime(2027, 2, 14, 23, 30, tzinfo=UTC)


def season(year: int, final_at: datetime | None = SB_2026, final: bool = False) -> SeasonInfo:
    return SeasonInfo(year, final_at, final)


def test_during_season() -> None:
    assert active_season(datetime(2026, 10, 29, tzinfo=UTC), [season(2026)]) == 2026


def test_rolls_over_once_super_bowl_final() -> None:
    now = datetime(2027, 2, 15, 3, 0, tzinfo=UTC)
    assert active_season(now, [season(2026, final=True)]) == 2027


def test_rolls_over_one_day_after_scheduled_super_bowl() -> None:
    assert active_season(datetime(2027, 2, 15, 23, 29, tzinfo=UTC), [season(2026)]) == 2026
    assert active_season(datetime(2027, 2, 15, 23, 30, tzinfo=UTC), [season(2026)]) == 2027


def test_next_season_known_but_not_released() -> None:
    now = datetime(2027, 3, 1, tzinfo=UTC)
    assert active_season(now, [season(2026, final=True), season(2027, final_at=None)]) == 2027


def test_no_rows_uses_calendar() -> None:
    assert active_season(datetime(2027, 1, 20, tzinfo=UTC), []) == 2026
    assert active_season(datetime(2026, 9, 1, tzinfo=UTC), []) == 2026
