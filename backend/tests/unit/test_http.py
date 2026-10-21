import httpx
import pytest
import respx

from app.core.http import ProviderClient, ProviderDisabled
from tests.conftest import make_settings

URL = "https://api.example.test/games"


def client(**settings: object) -> ProviderClient:
    return ProviderClient(make_settings(**settings), retry_base_s=0)


async def test_kill_switch_blocks_calls() -> None:
    with respx.mock:
        route = respx.get(URL)
        with pytest.raises(ProviderDisabled):
            await client(provider_apisports_enabled=False).request(
                "apisports", "GET", URL, endpoint="games"
            )
    assert not route.called


async def test_retries_5xx_then_succeeds() -> None:
    with respx.mock:
        route = respx.get(URL).mock(
            side_effect=[httpx.Response(503), httpx.Response(502), httpx.Response(200, json=[])]
        )
        response = await client().request("apisports", "GET", URL, endpoint="games")
    assert response.status_code == 200
    assert route.call_count == 3


async def test_gives_up_after_three_attempts_and_returns_last_response() -> None:
    with respx.mock:
        route = respx.get(URL).mock(return_value=httpx.Response(500))
        response = await client().request("apisports", "GET", URL, endpoint="games")
    assert response.status_code == 500
    assert route.call_count == 3


async def test_4xx_is_not_retried() -> None:
    with respx.mock:
        route = respx.get(URL).mock(return_value=httpx.Response(404))
        response = await client().request("apisports", "GET", URL, endpoint="games")
    assert response.status_code == 404
    assert route.call_count == 1


async def test_429_honors_retry_after() -> None:
    with respx.mock:
        route = respx.get(URL).mock(
            side_effect=[httpx.Response(429, headers={"Retry-After": "0"}), httpx.Response(200)]
        )
        response = await client().request("apisports", "GET", URL, endpoint="games")
    assert response.status_code == 200
    assert route.call_count == 2


async def test_network_errors_are_retried_then_raised() -> None:
    with respx.mock:
        route = respx.get(URL).mock(side_effect=httpx.ConnectError("down"))
        with pytest.raises(httpx.ConnectError):
            await client().request("apisports", "GET", URL, endpoint="games")
    assert route.call_count == 3
