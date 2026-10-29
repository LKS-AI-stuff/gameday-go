"""User A can't read or change user B's data through the M1 endpoints (FR-A5, AC-27)."""

from collections.abc import Callable

import httpx
import pytest

from tests.integration.test_preferences import API, onboarding

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("season_data")]


async def test_users_only_see_their_own_preferences_and_favorites(
    api: httpx.AsyncClient, new_user: Callable[..., dict[str, str]]
) -> None:
    alice, bob = new_user(email="alice@example.com"), new_user(email="bob@example.com")
    await api.put(
        f"{API}/me/preferences", headers=alice, json=onboarding(favorite_team_ids=["CHI"])
    )
    await api.put(
        f"{API}/me/preferences",
        headers=bob,
        json=onboarding(favorite_team_ids=["KC"], home_zip="64129", timezone="America/Denver"),
    )
    bob_settings = {
        "level": "off",
        "categories": {
            "watch_hit": False,
            "schedule_change": False,
            "reminder": False,
            "digest": False,
        },
    }
    await api.put(f"{API}/me/notification-settings", headers=bob, json=bob_settings)

    alice_prefs = (await api.get(f"{API}/me/preferences", headers=alice)).json()
    assert alice_prefs["favorite_team_ids"] == ["CHI"]
    assert alice_prefs["home_zip"] == "60601"
    assert alice_prefs["timezone"] == "America/Chicago"
    alice_settings = (await api.get(f"{API}/me/notification-settings", headers=alice)).json()
    assert alice_settings["level"] == "medium"

    page = (
        await api.get(f"{API}/games", headers=alice, params={"favorites": "true", "limit": 100})
    ).json()
    assert page["items"]
    for game in page["items"]:
        assert "CHI" in {game["home"]["id"], game["away"]["id"]}
        assert game["is_favorite"] is True
    bob_page = (await api.get(f"{API}/games", headers=bob, params={"favorites": "true"})).json()
    assert all("KC" in {g["home"]["id"], g["away"]["id"]} for g in bob_page["items"])
