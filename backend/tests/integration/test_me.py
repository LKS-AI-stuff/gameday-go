"""User provisioning, age confirmation and per-user isolation (FR-A3, FR-A5)."""

import asyncio
import uuid

import asyncpg
import httpx
import pytest

from tests.conftest import TokenFactory
from tests.integration.conftest import auth

pytestmark = pytest.mark.db


async def test_first_request_provisions_user(
    api: httpx.AsyncClient,
    make_token: TokenFactory,
    user_ids: list[str],
    app_conn: asyncpg.Connection,
) -> None:
    sub = str(uuid.uuid4())
    user_ids.append(sub)
    token = make_token(sub=sub, email="ben@example.com")

    first = await api.get("/api/v1/me", headers=auth(token))
    second = await api.get("/api/v1/me", headers=auth(token))

    assert first.status_code == 200
    assert first.json() == {
        "id": sub,
        "email": "ben@example.com",
        "age_confirmed": True,
        "timezone": None,
        "onboarded": False,
    }
    assert second.json() == first.json()
    assert (
        await app_conn.fetchval("select count(*) from app.users where id = $1", uuid.UUID(sub)) == 1
    )


async def test_concurrent_first_requests_create_one_row(
    api: httpx.AsyncClient,
    make_token: TokenFactory,
    user_ids: list[str],
    app_conn: asyncpg.Connection,
) -> None:
    sub = str(uuid.uuid4())
    user_ids.append(sub)
    token = make_token(sub=sub)
    responses = await asyncio.gather(
        *(api.get("/api/v1/me", headers=auth(token)) for _ in range(5))
    )
    assert {r.status_code for r in responses} == {200}
    assert (
        await app_conn.fetchval("select count(*) from app.users where id = $1", uuid.UUID(sub)) == 1
    )


async def test_age_confirmation(
    api: httpx.AsyncClient, make_token: TokenFactory, user_ids: list[str]
) -> None:
    sub = str(uuid.uuid4())
    user_ids.append(sub)
    token = make_token(sub=sub, age_confirmed=False)

    me = await api.get("/api/v1/me", headers=auth(token))
    assert me.json()["age_confirmed"] is False

    confirmed = await api.post("/api/v1/me/age-confirmation", headers=auth(token))
    assert confirmed.status_code == 200
    assert confirmed.json()["age_confirmed"] is True
    again = await api.post("/api/v1/me/age-confirmation", headers=auth(token))
    assert again.json()["age_confirmed"] is True


async def test_each_user_sees_only_themselves(
    api: httpx.AsyncClient, make_token: TokenFactory, user_ids: list[str]
) -> None:
    a, b = str(uuid.uuid4()), str(uuid.uuid4())
    user_ids.extend([a, b])
    me_a = await api.get("/api/v1/me", headers=auth(make_token(sub=a, email="a@example.com")))
    me_b = await api.get("/api/v1/me", headers=auth(make_token(sub=b, email="b@example.com")))
    assert (me_a.json()["id"], me_a.json()["email"]) == (a, "a@example.com")
    assert (me_b.json()["id"], me_b.json()["email"]) == (b, "b@example.com")


async def test_ready_checks_the_database(api: httpx.AsyncClient) -> None:
    response = await api.get("/api/v1/ready")
    assert response.status_code == 200
