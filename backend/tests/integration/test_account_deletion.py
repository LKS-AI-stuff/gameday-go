"""Account deletion (FR-A4): every M1 user row goes, then the sign-in account."""

from collections.abc import Callable

import asyncpg
import httpx
import pytest

from app.core.supabase_admin import SupabaseAdmin
from tests.conftest import make_settings
from tests.integration.test_preferences import API, onboarding

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("reference_data")]

USER_TABLES = ("user_preferences", "user_favorite_teams", "notification_settings", "app_events")


def admin_returning(*statuses: int) -> tuple[SupabaseAdmin, list[httpx.Request]]:
    seen: list[httpx.Request] = []
    responses = iter(statuses)

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(next(responses))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = make_settings(supabase_secret_key="test-secret")
    return SupabaseAdmin(settings, http_client=client, retry_base_s=0), seen


async def onboarded_user(
    api: httpx.AsyncClient, new_user: Callable[..., dict[str, str]]
) -> tuple[dict[str, str], str]:
    headers = new_user()
    await api.put(f"{API}/me/preferences", headers=headers, json=onboarding())
    await api.post(
        f"{API}/app-events",
        headers=headers,
        json={
            "events": [
                {
                    "name": "onboarding_completed",
                    "platform": "web",
                    "client_ts": "2026-10-29T12:00:00Z",
                }
            ]
        },
    )
    me = (await api.get(f"{API}/me", headers=headers)).json()
    return headers, me["id"]


async def count_rows(conn: asyncpg.Connection, user_id: str) -> dict[str, int]:
    counts = {"users": await conn.fetchval("select count(*) from app.users where id = $1", user_id)}
    for table in USER_TABLES:
        counts[table] = await conn.fetchval(
            f"select count(*) from app.{table} where user_id = $1",  # noqa: S608
            user_id,
        )
    return counts


async def test_delete_account_removes_all_rows_and_auth_user(
    api: httpx.AsyncClient,
    new_user: Callable[..., dict[str, str]],
    app_conn: asyncpg.Connection,
) -> None:
    headers, user_id = await onboarded_user(api, new_user)
    admin, seen = admin_returning(204)
    api._transport.app.state.supabase_admin = admin  # type: ignore[attr-defined]
    assert all(v > 0 for v in (await count_rows(app_conn, user_id)).values())

    response = await api.delete(f"{API}/me", headers=headers)

    assert response.status_code == 204
    assert set((await count_rows(app_conn, user_id)).values()) == {0}
    assert len(seen) == 1
    assert seen[0].method == "DELETE" and seen[0].url.path.endswith(f"/admin/users/{user_id}")
    assert seen[0].headers["apikey"] == "test-secret"


async def test_already_deleted_auth_user_counts_as_done(
    api: httpx.AsyncClient, new_user: Callable[..., dict[str, str]]
) -> None:
    headers, _ = await onboarded_user(api, new_user)
    admin, _ = admin_returning(404)
    api._transport.app.state.supabase_admin = admin  # type: ignore[attr-defined]
    assert (await api.delete(f"{API}/me", headers=headers)).status_code == 204


async def test_auth_failure_returns_503_and_retry_converges(
    api: httpx.AsyncClient,
    new_user: Callable[..., dict[str, str]],
    app_conn: asyncpg.Connection,
) -> None:
    headers, user_id = await onboarded_user(api, new_user)
    admin, seen = admin_returning(500, 500, 500, 204)
    api._transport.app.state.supabase_admin = admin  # type: ignore[attr-defined]

    failed = await api.delete(f"{API}/me", headers=headers)
    assert failed.status_code == 503
    assert failed.json()["code"] == "auth_deletion_failed"
    # Personal data is already gone after the first call (FR-A4).
    assert set((await count_rows(app_conn, user_id)).values()) == {0}

    retried = await api.delete(f"{API}/me", headers=headers)
    assert retried.status_code == 204
    assert len(seen) == 4
    assert set((await count_rows(app_conn, user_id)).values()) == {0}
