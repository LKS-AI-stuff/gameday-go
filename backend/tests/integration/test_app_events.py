"""Product events (TDD §15.1, SM1): allowlisted names, no free text, caller's user ID."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg
import httpx
import pytest

from tests.integration.test_preferences import API

pytestmark = pytest.mark.db


def event(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": "onboarding_started",
        "platform": "ios",
        "client_ts": datetime.now(UTC).isoformat(),
    }
    body.update(overrides)
    return body


async def test_events_are_stored_for_the_caller(
    api: httpx.AsyncClient,
    new_user: Callable[..., dict[str, str]],
    app_conn: asyncpg.Connection,
) -> None:
    headers = new_user()
    me = (await api.get(f"{API}/me", headers=headers)).json()
    batch = {"events": [event(), event(name="onboarding_completed")]}
    assert (await api.post(f"{API}/app-events", headers=headers, json=batch)).status_code == 202
    rows = await app_conn.fetch(
        "select name, platform, props from app.app_events where user_id = $1 order by name",
        me["id"],
    )
    assert [(r["name"], r["platform"], r["props"]) for r in rows] == [
        ("onboarding_completed", "ios", "{}"),
        ("onboarding_started", "ios", "{}"),
    ]


@pytest.mark.parametrize(
    "batch",
    [
        {"events": [event(name="page_view")]},
        {"events": [event(props={"email": "a@b.c"})]},
        {"events": [event(platform="desktop")]},
        {"events": []},
        {"events": [event()] * 21},
        {"events": [event(client_ts=(datetime.now(UTC) - timedelta(days=3)).isoformat())]},
        {"events": [event(client_ts="2026-10-29T12:00:00")]},
    ],
)
async def test_invalid_events_are_rejected(
    api: httpx.AsyncClient, new_user: Callable[..., dict[str, str]], batch: dict[str, Any]
) -> None:
    response = await api.post(f"{API}/app-events", headers=new_user(), json=batch)
    assert response.status_code == 422
