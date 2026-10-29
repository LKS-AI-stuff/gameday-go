import uuid
from datetime import UTC, date, datetime, time

import pytest

from app.domain.models import GameFacts, TeamFacts
from app.domain.significance import is_primetime, rivalry_key, schedule_tags

TEAMS = {
    "CHI": TeamFacts("CHI", "NFC", "North"),
    "GB": TeamFacts("GB", "NFC", "North"),
    "DAL": TeamFacts("DAL", "NFC", "East"),
    "KC": TeamFacts("KC", "AFC", "West"),
    "BUF": TeamFacts("BUF", "AFC", "East"),
}
RIVALRIES = {rivalry_key("KC", "BUF"): "Repeated high-stakes playoff meetings"}
SEVEN_PM = time(19, 0)


def game(
    home: str | None,
    away: str | None,
    kickoff: datetime | None = datetime(2026, 11, 8, 18, 0, tzinfo=UTC),
    stage: str = "regular",
    country: str | None = "US",
    day: date | None = None,
) -> GameFacts:
    return GameFacts(
        id=uuid.uuid4(),
        season=2026,
        week=9,
        stage=stage,  # type: ignore[arg-type]
        home_team_id=home,
        away_team_id=away,
        game_date=day or (kickoff.date() if kickoff else None),
        kickoff_at=kickoff,
        venue_country=country,
    )


def tags_of(games: list[GameFacts], target: GameFacts) -> set[str]:
    return {t.tag for t in schedule_tags(games, TEAMS, RIVALRIES, SEVEN_PM)[target.id]}


def test_division_rivalry() -> None:
    g = game("GB", "CHI")
    other = game("DAL", "CHI")
    assert "division_rivalry" in tags_of([g, other], g)
    assert "division_rivalry" not in tags_of([g, other], other)


@pytest.mark.parametrize(("home", "away"), [("KC", "BUF"), ("BUF", "KC")])
def test_featured_rivalry_in_either_order(home: str, away: str) -> None:
    g = game(home, away)
    result = schedule_tags([g], TEAMS, RIVALRIES, SEVEN_PM)[g.id]
    featured = [t for t in result if t.tag == "featured_rivalry"]
    assert featured and featured[0].weight == "high"
    assert featured[0].detail == "Repeated high-stakes playoff meetings"


def test_tbd_playoff_game_gets_only_playoff_tag() -> None:
    g = game(None, None, kickoff=None, stage="playoff", country=None, day=date(2027, 1, 16))
    assert tags_of([g], g) == {"playoff"}


def test_playoff_with_known_teams_keeps_rivalry() -> None:
    g = game("GB", "CHI", stage="playoff")
    assert {"playoff", "division_rivalry"} <= tags_of([g], g)


@pytest.mark.parametrize(
    ("kickoff", "expected"),
    [
        (datetime(2026, 11, 9, 1, 20, tzinfo=UTC), True),  # Sun 8:20 PM ET
        (datetime(2026, 11, 9, 0, 0, tzinfo=UTC), True),  # Sun 7:00 PM ET
        (datetime(2026, 11, 8, 23, 59, tzinfo=UTC), False),  # Sun 6:59 PM ET
        (datetime(2026, 11, 6, 1, 15, tzinfo=UTC), True),  # Thu 8:15 PM ET
        (datetime(2026, 11, 10, 1, 15, tzinfo=UTC), True),  # Mon 8:15 PM ET
        (datetime(2026, 12, 20, 1, 0, tzinfo=UTC), False),  # Sat 8:00 PM ET
        (datetime(2026, 11, 8, 18, 0, tzinfo=UTC), False),  # Sun 1:00 PM ET
        (None, False),
    ],
)
def test_primetime(kickoff: datetime | None, expected: bool) -> None:
    assert is_primetime(kickoff, SEVEN_PM) is expected


def test_primetime_across_dst_change() -> None:
    # Nov 1, 2026: clocks fall back. 00:00 UTC is 8 PM EDT on Sat Oct 31, 7 PM EST on Sun Nov 8.
    assert is_primetime(datetime(2026, 11, 9, 0, 0, tzinfo=UTC), SEVEN_PM)
    assert not is_primetime(datetime(2026, 11, 1, 22, 30, tzinfo=UTC), SEVEN_PM)


def test_home_opener_and_finale_per_team() -> None:
    first = game("CHI", "DAL", kickoff=datetime(2026, 9, 13, 17, 0, tzinfo=UTC))
    middle = game("CHI", "KC", kickoff=datetime(2026, 10, 4, 17, 0, tzinfo=UTC))
    last = game("CHI", "BUF", kickoff=datetime(2027, 1, 3, 18, 0, tzinfo=UTC))
    away = game("GB", "CHI", kickoff=datetime(2026, 9, 6, 17, 0, tzinfo=UTC))
    games = [middle, last, first, away]
    assert "home_opener" in tags_of(games, first)
    assert "home_finale" in tags_of(games, last)
    assert not {"home_opener", "home_finale"} & tags_of(games, middle)
    # GB's only home game is both its opener and its finale.
    assert {"home_opener", "home_finale"} <= tags_of(games, away)


def test_international_game_tagged_and_not_a_home_opener() -> None:
    london = game("CHI", "DAL", kickoff=datetime(2026, 9, 6, 13, 30, tzinfo=UTC), country="GB")
    home = game("CHI", "KC", kickoff=datetime(2026, 9, 13, 17, 0, tzinfo=UTC))
    result = schedule_tags([london, home], TEAMS, RIVALRIES, SEVEN_PM)
    london_tags = {t.tag: t.weight for t in result[london.id]}
    assert london_tags.get("international") == "info"
    assert "home_opener" not in london_tags
    assert "home_opener" in {t.tag for t in result[home.id]}


def test_unknown_country_is_not_international() -> None:
    g = game("CHI", "DAL", country=None)
    assert "international" not in tags_of([g], g)
