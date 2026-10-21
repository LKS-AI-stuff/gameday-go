"""API behavior that needs no database."""

from collections.abc import AsyncIterator

import httpx
import pytest

from app.core.auth import TokenVerifier
from app.main_api import create_app
from tests.conftest import make_settings


@pytest.fixture
async def api() -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(make_settings())
    app.state.token_verifier = TokenVerifier(make_settings())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_health(api: httpx.AsyncClient) -> None:
    response = await api.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


async def test_me_requires_a_token(api: httpx.AsyncClient) -> None:
    response = await api.get("/api/v1/me")
    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "not_authenticated"


async def test_malformed_token_is_401(api: httpx.AsyncClient) -> None:
    response = await api.get("/api/v1/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_token"


async def test_unknown_route_is_problem_json(api: httpx.AsyncClient) -> None:
    response = await api.get("/api/v1/nope")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_docs_are_disabled_in_production() -> None:
    app = create_app(make_settings(app_env="production"))
    assert app.docs_url is None
    assert app.openapi_url is None
