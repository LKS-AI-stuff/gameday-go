"""Browsing the recorded 2026 season (FR-SC1-SC5, FR-SC8, FR-SC4, AC-47)."""

from collections.abc import Callable
from datetime import timedelta

import asyncpg
import httpx
import pytest

from tests.integration.conftest import NOW
from tests.integration.test_preferences import API, onboarding

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("season_data")]

Headers = Callable[..., dict[str, str]]


@pytest.fixture
async def fan(api: httpx.AsyncClient, new_user: Headers) -> dict[str, str]:
    """A Chicago fan with Low travel."""
    headers = new_user()
    await api.put(
        f"{API}/me/preferences",
        headers=headers,
        json=onboarding(favorite_team_ids=["CHI"], travel="low"),
    )
    return headers


async def test_teams(api: httpx.AsyncClient, fan: dict[str, str]) -> None:
    teams = (await api.get(f"{API}/teams", headers=fan)).json()
    assert len(teams) == 32
    bears = next(t for t in teams if t["id"] == "CHI")
    assert bears == {
        "id": "CHI",
        "name": "Chicago Bears",
        "nickname": "Bears",
        "city": "Chicago",
        "conference": "NFC",
        "division": "North",
    }


async def test_season(
    api: httpx.AsyncClient, fan: dict[str, str], app_conn: asyncpg.Connection
) -> None:
    season = (await api.get(f"{API}/season", headers=fan)).json()
    expected_week = await app_conn.fetchval(
        "select week from app.games where season = 2026 and sort_at >= $1 order by sort_at limit 1",
        NOW - timedelta(hours=12),
    )
    assert season["year"] == 2026
    assert season["status"] == "active"
    assert season["schedule_available"] is True
    assert season["current_week"] == expected_week
    assert season["planning_window_days"] == 30
    assert season["schedule_updated_at"] is not None
    assert season["source"] == "API-Sports"
    labels = {w["week"]: w["label"] for w in season["weeks"]}
    assert labels[1] == "WEEK 1" and labels[19] == "WILD CARD"


async def test_week_filter_orders_by_kickoff_with_tbd_last(
    api: httpx.AsyncClient, fan: dict[str, str]
) -> None:
    page = (await api.get(f"{API}/games", headers=fan, params={"week": 16})).json()
    items = page["items"]
    assert len(items) == 16 and page["next_cursor"] is None
    assert all(g["week"] == 16 and g["week_label"] == "WEEK 16" for g in items)
    tbd = [g for g in items if g["kickoff_tbd"]]
    assert tbd and all(g["kickoff_at"] is None for g in tbd)
    # Each TBD game sorts after the timed games on its day.
    for game in tbd:
        same_day = [g for g in items if g["game_date"] == game["game_date"]]
        assert same_day.index(game) >= len([g for g in same_day if not g["kickoff_tbd"]])


async def test_team_filter_and_bye_week(
    api: httpx.AsyncClient, fan: dict[str, str], app_conn: asyncpg.Connection
) -> None:
    played = {
        r["week"]
        for r in await app_conn.fetch(
            "select week from app.games where season = 2026 and stage = 'regular' "
            "and 'CHI' in (home_team_id, away_team_id)"
        )
    }
    bye = next(w for w in range(1, 19) if w not in played)
    response = await api.get(f"{API}/games", headers=fan, params={"week": bye, "team": "CHI"})
    assert response.json()["items"] == []
    some_week = min(played)
    games = (
        await api.get(f"{API}/games", headers=fan, params={"week": some_week, "team": "CHI"})
    ).json()
    assert len(games["items"]) == 1


async def test_favorites_pagination(api: httpx.AsyncClient, fan: dict[str, str]) -> None:
    first = (
        await api.get(f"{API}/games", headers=fan, params={"favorites": "true", "limit": 2})
    ).json()
    assert len(first["items"]) == 2 and first["next_cursor"]
    second = (
        await api.get(
            f"{API}/games",
            headers=fan,
            params={"favorites": "true", "limit": 2, "cursor": first["next_cursor"]},
        )
    ).json()
    first_ids = {g["id"] for g in first["items"]}
    assert first_ids.isdisjoint({g["id"] for g in second["items"]})
    everything = (
        await api.get(f"{API}/games", headers=fan, params={"favorites": "true", "limit": 100})
    ).json()
    assert len(everything["items"]) == 17  # one regular season, no playoff teams known yet
    bad = await api.get(f"{API}/games", headers=fan, params={"cursor": "not-a-cursor"})
    assert bad.status_code == 422 and bad.json()["code"] == "invalid_cursor"


async def test_upcoming_favorites_from_now(api: httpx.AsyncClient, fan: dict[str, str]) -> None:
    """Home's "Your next games" source (FR-SC1)."""
    page = (
        await api.get(
            f"{API}/games",
            headers=fan,
            params={"favorites": "true", "from": NOW.isoformat(), "limit": 5},
        )
    ).json()
    kickoffs = [g["kickoff_at"] or g["game_date"] for g in page["items"]]
    assert kickoffs == sorted(kickoffs)
    assert all(g["planning"]["status"] != "closed" for g in page["items"])


async def test_game_detail_tags_distance_source_and_planning(
    api: httpx.AsyncClient, fan: dict[str, str], app_conn: asyncpg.Connection
) -> None:
    game_id = await app_conn.fetchval(
        "select id from app.games where season = 2026 and home_team_id = 'CHI' and week = 9"
    )
    detail = (await api.get(f"{API}/games/{game_id}", headers=fan)).json()
    assert detail["home"]["nickname"] == "Bears"
    assert {"primetime"} <= {t["tag"] for t in detail["tags"]}
    assert detail["venue_name"] == "Soldier Field"
    assert detail["distance_mi"] is not None and detail["distance_mi"] < 5
    assert detail["planning"] == {"status": "open", "opens_at": None}
    assert detail["source"]["provider"] == "API-Sports"
    assert detail["source"]["schedule_updated_at"] is not None
    assert detail["travel_hint"] is None
    assert detail["is_favorite"] is True


async def test_planning_window_and_closed_games(
    api: httpx.AsyncClient, fan: dict[str, str], app_conn: asyncpg.Connection
) -> None:
    """AC-47: a game more than 30 days out shows when planning opens."""
    later = await app_conn.fetchrow(
        "select id, kickoff_at from app.games where season = 2026 and kickoff_at > $1 "
        "order by kickoff_at limit 1",
        NOW + timedelta(days=45),
    )
    assert later is not None
    detail = (await api.get(f"{API}/games/{later['id']}", headers=fan)).json()
    assert detail["planning"]["status"] == "opens_on"
    assert detail["planning"]["opens_at"].startswith(
        (later["kickoff_at"] - timedelta(days=30)).date().isoformat()
    )
    past = await app_conn.fetchval(
        "select id from app.games where season = 2026 and week = 1 limit 1"
    )
    assert (await api.get(f"{API}/games/{past}", headers=fan)).json()["planning"][
        "status"
    ] == "closed"


async def test_international_game_and_low_travel_hint(
    api: httpx.AsyncClient, fan: dict[str, str], app_conn: asyncpg.Connection
) -> None:
    game_id = await app_conn.fetchval(
        "select id from app.games where season = 2026 and venue_city = 'Madrid'"
    )
    detail = (await api.get(f"{API}/games/{game_id}", headers=fan)).json()
    assert {"tag": "international", "weight": "info", "detail": None} in detail["tags"]
    assert detail["venue_country"] == "ES"
    assert detail["travel_hint"] == "outside_travel_area"


async def test_tbd_playoff_games_show_placeholders(
    api: httpx.AsyncClient, fan: dict[str, str]
) -> None:
    page = (await api.get(f"{API}/games", headers=fan, params={"week": 19})).json()
    assert page["items"]
    for game in page["items"]:
        assert game["home"] is None and game["home_placeholder"] == "TBD"
        assert [t["tag"] for t in game["tags"]] == ["playoff"]
        assert game["kickoff_tbd"] is True


async def test_unknown_game_is_404(api: httpx.AsyncClient, fan: dict[str, str]) -> None:
    response = await api.get(f"{API}/games/00000000-0000-0000-0000-000000000000", headers=fan)
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_from_and_to_need_a_time_zone(api: httpx.AsyncClient, fan: dict[str, str]) -> None:
    response = await api.get(f"{API}/games", headers=fan, params={"from": "2026-11-01T00:00:00"})
    assert response.status_code == 422
    assert response.json()["code"] == "naive_datetime"
