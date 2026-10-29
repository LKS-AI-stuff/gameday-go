"""Onboarding preferences, notification settings and ZIP lookup (FR-P1-P4, BR-N9, AC-1, AC-2)."""

from collections.abc import Callable
from typing import Any

import asyncpg
import httpx
import pytest

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("reference_data")]

API = "/api/v1"
Headers = Callable[..., dict[str, str]]


def onboarding(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "favorite_team_ids": ["CHI", "DET"],
        "home_zip": "60601",
        "travel": "medium",
        "spending": "less",
        "max_ticket_price_usd": 90,
        "viewing": "bar",
        "notification_level": "medium",
        "timezone": "America/Chicago",
    }
    body.update(overrides)
    return body


async def test_onboarding_saves_six_preferences_and_time_zone(
    api: httpx.AsyncClient, new_user: Headers, app_conn: asyncpg.Connection
) -> None:
    headers = new_user()
    assert (await api.get(f"{API}/me", headers=headers)).json()["onboarded"] is False
    assert (await api.get(f"{API}/me/preferences", headers=headers)).status_code == 404

    saved = await api.put(f"{API}/me/preferences", headers=headers, json=onboarding())

    assert saved.status_code == 200
    assert saved.json() == {
        "favorite_team_ids": ["CHI", "DET"],
        "home_zip": "60601",
        "home_place": {"place_name": "Chicago", "state": "IL"},
        "travel": "medium",
        "spending": "less",
        "max_ticket_price_usd": 90,
        "viewing": "bar",
        "notification_level": "medium",
        "timezone": "America/Chicago",
    }
    me = (await api.get(f"{API}/me", headers=headers)).json()
    assert me["onboarded"] is True
    assert me["timezone"] == "America/Chicago"
    row = await app_conn.fetchrow(
        "select max_ticket_price_cents from app.user_preferences where user_id = $1", me["id"]
    )
    assert row is not None and row["max_ticket_price_cents"] == 9000
    categories = await app_conn.fetch(
        "select category, email_enabled from app.notification_settings where user_id = $1",
        me["id"],
    )
    assert {(r["category"], r["email_enabled"]) for r in categories} == {
        ("watch_hit", True),
        ("schedule_change", True),
        ("reminder", True),
        ("digest", True),
    }


async def test_only_the_six_preferences_are_accepted(
    api: httpx.AsyncClient, new_user: Headers
) -> None:
    """AC-1: no other onboarding questions, so extra fields are rejected."""
    response = await api.put(
        f"{API}/me/preferences", headers=new_user(), json=onboarding(party_size=2)
    )
    assert response.status_code == 422


async def test_favorites_add_remove_and_keep_at_least_one(
    api: httpx.AsyncClient, new_user: Headers
) -> None:
    """AC-2."""
    headers = new_user()
    await api.put(f"{API}/me/preferences", headers=headers, json=onboarding())

    added = await api.put(
        f"{API}/me/preferences",
        headers=headers,
        json=onboarding(favorite_team_ids=["CHI", "DET", "GB"]),
    )
    assert added.json()["favorite_team_ids"] == ["CHI", "DET", "GB"]
    removed = await api.put(
        f"{API}/me/preferences", headers=headers, json=onboarding(favorite_team_ids=["GB"])
    )
    assert removed.json()["favorite_team_ids"] == ["GB"]
    empty = await api.put(
        f"{API}/me/preferences", headers=headers, json=onboarding(favorite_team_ids=[])
    )
    assert empty.status_code == 422
    current = await api.get(f"{API}/me/preferences", headers=headers)
    assert current.json()["favorite_team_ids"] == ["GB"]


@pytest.mark.parametrize(
    ("override", "code"),
    [
        ({"favorite_team_ids": ["XYZ"]}, "unknown_team"),
        ({"home_zip": "00000"}, "zip_not_found"),
        ({"timezone": "Mars/Olympus"}, "invalid_timezone"),
        ({"home_zip": "6060"}, "validation_error"),
        ({"max_ticket_price_usd": 0}, "validation_error"),
        ({"travel": "extreme"}, "validation_error"),
    ],
)
async def test_invalid_preferences_are_rejected(
    api: httpx.AsyncClient, new_user: Headers, override: dict[str, Any], code: str
) -> None:
    response = await api.put(
        f"{API}/me/preferences", headers=new_user(), json=onboarding(**override)
    )
    assert response.status_code == 422
    assert response.json()["code"] == code


async def test_max_ticket_price_is_optional(api: httpx.AsyncClient, new_user: Headers) -> None:
    response = await api.put(
        f"{API}/me/preferences", headers=new_user(), json=onboarding(max_ticket_price_usd=None)
    )
    assert response.json()["max_ticket_price_usd"] is None


async def test_notification_settings_round_trip(api: httpx.AsyncClient, new_user: Headers) -> None:
    headers = new_user()
    url = f"{API}/me/notification-settings"
    assert (await api.get(url, headers=headers)).status_code == 404
    await api.put(f"{API}/me/preferences", headers=headers, json=onboarding())

    assert (await api.get(url, headers=headers)).json() == {
        "level": "medium",
        "categories": {
            "watch_hit": True,
            "schedule_change": True,
            "reminder": True,
            "digest": True,
        },
    }
    body = {
        "level": "low",
        "categories": {
            "watch_hit": True,
            "schedule_change": False,
            "reminder": False,
            "digest": False,
        },
    }
    assert (await api.put(url, headers=headers, json=body)).json() == body
    prefs = (await api.get(f"{API}/me/preferences", headers=headers)).json()
    assert prefs["notification_level"] == "low"


async def test_zip_lookup(api: httpx.AsyncClient, new_user: Headers) -> None:
    headers = new_user()
    found = await api.get(f"{API}/zip/60601", headers=headers)
    assert found.json() == {"zip": "60601", "place_name": "Chicago", "state": "IL"}
    missing = await api.get(f"{API}/zip/00000", headers=headers)
    assert missing.status_code == 404 and missing.json()["code"] == "zip_not_found"
    assert (await api.get(f"{API}/zip/abc12", headers=headers)).status_code == 422


async def test_nearest_zip_for_use_my_location(api: httpx.AsyncClient, new_user: Headers) -> None:
    headers = new_user()
    loop = await api.post(
        f"{API}/zip/nearest", headers=headers, json={"lat": 41.886, "lng": -87.62}
    )
    assert loop.status_code == 200
    assert loop.json()["zip"].startswith("606")
    assert loop.json()["place_name"] == "Chicago"
    ocean = await api.post(f"{API}/zip/nearest", headers=headers, json={"lat": 35.0, "lng": -40.0})
    assert ocean.status_code == 404
    bad = await api.post(f"{API}/zip/nearest", headers=headers, json={"lat": 95, "lng": 0})
    assert bad.status_code == 422


async def test_data_endpoints_need_the_age_confirmation(
    api: httpx.AsyncClient, new_user: Headers
) -> None:
    headers = new_user(age_confirmed=False)
    response = await api.get(f"{API}/zip/60601", headers=headers)
    assert response.status_code == 403
    assert response.json()["code"] == "age_confirmation_required"
