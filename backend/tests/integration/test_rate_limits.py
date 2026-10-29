"""Per-user and per-IP request limits (NFR-15)."""

from collections.abc import Callable

import httpx
import pytest

from tests.integration.test_preferences import API

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("reference_data")]


async def test_61st_request_in_a_minute_is_limited(
    api: httpx.AsyncClient, new_user: Callable[..., dict[str, str]]
) -> None:
    headers, other = new_user(), new_user()
    statuses = [(await api.get(f"{API}/teams", headers=headers)).status_code for _ in range(61)]
    assert statuses.count(200) == 60
    limited = await api.get(f"{API}/teams", headers=headers)
    assert limited.status_code == 429
    assert limited.json()["code"] == "rate_limited"
    assert int(limited.headers["Retry-After"]) >= 1
    # Limits are per user.
    assert (await api.get(f"{API}/teams", headers=other)).status_code == 200


async def test_unauthenticated_routes_are_limited_per_ip(api: httpx.AsyncClient) -> None:
    statuses = [(await api.get(f"{API}/health")).status_code for _ in range(61)]
    assert statuses[:60] == [200] * 60
    assert statuses[60] == 429
