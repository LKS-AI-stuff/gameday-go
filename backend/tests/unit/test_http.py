import httpx
import pytest
import respx

from app.core.budgets import BudgetExhausted, BudgetState
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


class FakeBudgets:
    """Stands in for BudgetStore: `available` units, then BudgetExhausted."""

    def __init__(self, available: int) -> None:
        self.available = available
        self.consumed: list[bool] = []

    def is_budgeted(self, provider: str) -> bool:
        return provider == "apisports"

    async def consume(self, provider: str, *, allow_reserved: bool = False) -> BudgetState:
        if self.available <= 0:
            raise BudgetExhausted("apisports")
        self.available -= 1
        self.consumed.append(allow_reserved)
        return BudgetState(used=len(self.consumed), daily_limit=100, reserved=10)


def budgeted(budgets: FakeBudgets) -> ProviderClient:
    return ProviderClient(make_settings(), retry_base_s=0, budgets=budgets)  # type: ignore[arg-type]


async def test_budget_exhausted_sends_nothing() -> None:
    with respx.mock:
        route = respx.get(URL)
        with pytest.raises(BudgetExhausted):
            await budgeted(FakeBudgets(0)).request("apisports", "GET", URL, endpoint="games")
    assert not route.called


async def test_every_retry_consumes_budget() -> None:
    budgets = FakeBudgets(5)
    with respx.mock:
        respx.get(URL).mock(side_effect=[httpx.Response(503), httpx.Response(200)])
        await budgeted(budgets).request("apisports", "GET", URL, endpoint="games")
    assert budgets.consumed == [False, False]


async def test_reserved_budget_only_when_asked() -> None:
    budgets = FakeBudgets(1)
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200))
        await budgeted(budgets).request(
            "apisports", "GET", URL, endpoint="games", allow_reserved=True
        )
    assert budgets.consumed == [True]


async def test_unbudgeted_provider_skips_the_budget() -> None:
    budgets = FakeBudgets(0)
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200))
        response = await budgeted(budgets).request("places", "GET", URL, endpoint="search")
    assert response.status_code == 200
