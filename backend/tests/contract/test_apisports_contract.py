"""API-Sports adapter against recorded 2026 responses (T4; TDD §8.3; FR-LS10, BR-W3).

Fixtures were fetched once with the live key (league 1, season 2026) and contain no secrets.
"""

import logging
from datetime import UTC, date, datetime

import httpx
import pytest
import respx

from app.core.http import ProviderClient
from app.domain.models import GameStatus, ProviderGame
from app.providers.apisports import mapping
from app.providers.apisports.live import ApiSportsProvider
from app.providers.apisports.mock import load_fixture
from app.providers.errors import ProviderError
from tests.conftest import make_settings

RETRIEVED = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)
BASE = "https://v1.american-football.api-sports.io"


@pytest.fixture(scope="module")
def games() -> list[ProviderGame]:
    return mapping.map_games(load_fixture("games_2026"), 2026, RETRIEVED)


def test_preseason_and_pro_bowl_are_dropped(games: list[ProviderGame]) -> None:
    raw = load_fixture("games_2026")["response"]
    assert sum(1 for i in raw if i["game"]["stage"] == "Pre Season") == 49
    assert len(games) == 272 + 7  # regular season, listed playoff slots and the Super Bowl
    assert {g.stage for g in games} == {"regular", "playoff"}


def test_weeks_and_playoff_rounds(games: list[ProviderGame]) -> None:
    assert {g.week for g in games if g.stage == "regular"} == set(range(1, 19))
    assert sorted({g.week for g in games if g.stage == "playoff"}) == [19, 20, 21, 22]


def test_super_bowl_listed_as_pro_bowl_is_kept(games: list[ProviderGame]) -> None:
    super_bowl = [g for g in games if g.week == 22]
    assert len(super_bowl) == 1
    assert super_bowl[0].venue_name == "SoFi Stadium"
    assert super_bowl[0].kickoff_at == datetime(2027, 2, 14, 23, 30, tzinfo=UTC)


def test_a_named_super_bowl_wins_and_pro_bowl_is_dropped() -> None:
    payload = load_fixture("games_2026")
    pro_bowl = next(i for i in payload["response"] if i["game"]["week"] == "Pro Bowl")
    payload["response"].append(
        {**pro_bowl, "game": {**pro_bowl["game"], "id": 1, "week": "Super Bowl"}}
    )
    games = mapping.map_games(payload, 2026, RETRIEVED)
    assert [g.provider_game_id for g in games if g.week == 22] == ["1"]


def test_every_recorded_status_maps(games: list[ProviderGame]) -> None:
    assert {g.status for g in games} == {
        GameStatus.SCHEDULED,
        GameStatus.FINAL,
        GameStatus.FINAL_OT,
    }


def test_a_lone_midnight_utc_kickoff_is_a_real_8pm_game() -> None:
    """00:00 UTC is 8 PM EDT: one game at that time is real; a block of them is TBD."""
    payload = load_fixture("games_2026")
    item = next(
        i
        for i in payload["response"]
        if i["game"]["week"] == "Week 3" and i["game"]["stage"] == "Regular Season"
    )
    item["game"]["date"].update(date="2026-09-25", time="00:00", timestamp=1790294400)
    game = next(
        g
        for g in mapping.map_games(payload, 2026, RETRIEVED)
        if g.provider_game_id == str(item["game"]["id"])
    )
    assert game.kickoff_tbd is False
    assert game.kickoff_at == datetime(2026, 9, 25, 0, 0, tzinfo=UTC)
    assert game.game_date == date(2026, 9, 24)  # Thursday, 8 PM Eastern


def test_tbd_kickoffs_keep_their_game_day(games: list[ProviderGame]) -> None:
    tbd = [g for g in games if g.kickoff_tbd]
    assert len(tbd) == 24 + 6
    assert all(g.kickoff_at is None and g.game_date is not None for g in tbd)
    week18 = [g for g in tbd if g.week == 18]
    assert {g.game_date for g in week18} == {date(2027, 1, 10)}


def test_timed_kickoffs_are_utc_with_eastern_game_day(games: list[ProviderGame]) -> None:
    # Week 9 night games (UTC → Eastern game day): Thu 8:15 PM, Sun 8:20 PM, Mon 8:15 PM.
    night = {
        g.kickoff_at.date(): g.game_date
        for g in games
        if g.week == 9 and g.kickoff_at and g.kickoff_at.hour == 1
    }
    assert night == {
        date(2026, 11, 6): date(2026, 11, 5),
        date(2026, 11, 9): date(2026, 11, 8),
        date(2026, 11, 10): date(2026, 11, 9),
    }
    assert all(g.kickoff_at is None or g.kickoff_at.tzinfo == UTC for g in games)


def test_undecided_playoff_teams_are_none(games: list[ProviderGame]) -> None:
    playoff = [g for g in games if g.stage == "playoff"]
    assert all(g.home is None and g.away is None for g in playoff)


def test_teams_and_standings() -> None:
    teams = mapping.map_teams(load_fixture("teams_2026"))
    assert len(teams) == 32 and len({t.code for t in teams}) == 32
    bears = next(t for t in teams if t.code == "CHI")
    assert (bears.provider_team_id, bears.name, bears.city) == ("16", "Chicago Bears", "Chicago")
    standings = {
        s.provider_team_id: s for s in mapping.map_standings(load_fixture("standings_2026"))
    }
    assert len(standings) == 32
    assert (standings["16"].conference, standings["16"].division) == ("NFC", "North")


def test_unknown_status_before_kickoff_is_scheduled_after_is_skipped() -> None:
    item = load_fixture("games_2026")["response"][100]
    item["game"]["status"]["short"] = "XYZ"
    before = mapping.map_game(item, 2026, datetime(2026, 1, 1, tzinfo=UTC))
    after = mapping.map_game(item, 2026, datetime(2028, 1, 1, tzinfo=UTC))
    assert before is not None and before.status == GameStatus.SCHEDULED
    assert after is None


async def test_live_adapter_sends_league_season_and_key_and_never_logs_it(
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = make_settings(apisports_key="secret-key-123")
    with respx.mock:
        route = respx.get(f"{BASE}/teams").mock(
            return_value=httpx.Response(200, json=load_fixture("teams_2026"))
        )
        client = ProviderClient(settings, retry_base_s=0)
        with caplog.at_level(logging.DEBUG):
            teams = await ApiSportsProvider(client, settings).teams(2026)
        await client.aclose()
    request = route.calls.last.request
    assert request.url.params["league"] == "1" and request.url.params["season"] == "2026"
    assert request.headers["x-apisports-key"] == "secret-key-123"
    assert len(teams) == 32
    assert "secret-key-123" not in caplog.text


async def test_plan_errors_in_a_200_body_raise() -> None:
    settings = make_settings()
    body = {"errors": {"plan": "Free plans do not have access to this season"}, "response": []}
    with respx.mock:
        respx.get(f"{BASE}/games").mock(return_value=httpx.Response(200, json=body))
        client = ProviderClient(settings, retry_base_s=0)
        with pytest.raises(ProviderError) as exc:
            await ApiSportsProvider(client, settings).games_for_season(2026)
        await client.aclose()
    assert "Free plans" not in str(exc.value)
