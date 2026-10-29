"""Provider budget consumption is atomic (TDD §8.2, FR-O4a)."""

import asyncio
from datetime import date

import asyncpg
import pytest

from app.core.budgets import BudgetExhausted, BudgetStore
from app.db.session import get_engine
from tests.conftest import make_settings

pytestmark = pytest.mark.db

DAY = date(2001, 1, 1)


async def test_concurrent_consumption_never_exceeds_the_budget(
    migrated_db: object, app_conn: asyncpg.Connection
) -> None:
    await app_conn.execute("delete from app.provider_budgets where day = $1", DAY)
    store = BudgetStore(
        get_engine(), make_settings(apisports_daily_budget=12, apisports_reserve_pct=17)
    )

    async def take() -> bool:
        try:
            await store.consume("apisports", today=DAY)
        except BudgetExhausted:
            return False
        return True

    results = await asyncio.gather(*(take() for _ in range(20)))

    # 12 a day with ceil(12 * 17%) = 3 reserved: 9 available.
    assert results.count(True) == 9
    row = await app_conn.fetchrow("select * from app.provider_budgets where day = $1", DAY)
    assert (row["used"], row["daily_limit"], row["reserved"]) == (9, 12, 3)
    state = await store.consume("apisports", allow_reserved=True, today=DAY)
    assert state.used == 10
    await app_conn.execute("delete from app.provider_budgets where day = $1", DAY)
