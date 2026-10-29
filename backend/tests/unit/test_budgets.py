"""Budget warning at 80% of the daily limit, logged once (FR-O4a)."""

import logging
from types import TracebackType
from typing import Any

import pytest

from app.core.budgets import BudgetStore
from tests.conftest import make_settings


class FakeResult:
    def __init__(self, row: Any) -> None:
        self._row = row

    def first(self) -> Any:
        return self._row


class FakeEngine:
    """Stands in for the engine: every UPDATE succeeds and counts one more unit used."""

    def __init__(self, daily_limit: int) -> None:
        self.used = 0
        self.daily_limit = daily_limit

    def begin(self) -> "FakeEngine":
        return self

    async def __aenter__(self) -> "FakeEngine":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def execute(self, statement: Any, params: dict[str, Any]) -> FakeResult:
        if "UPDATE" not in str(statement):
            return FakeResult(None)
        self.used += 1
        row = type("Row", (), {"used": self.used, "daily_limit": self.daily_limit, "reserved": 0})
        return FakeResult(row)


async def test_warning_logged_once_at_80_percent(caplog: pytest.LogCaptureFixture) -> None:
    engine = FakeEngine(daily_limit=10)
    store = BudgetStore(engine, make_settings(apisports_daily_budget=10))  # type: ignore[arg-type]
    with caplog.at_level(logging.WARNING, logger="app.core.budgets"):
        for _ in range(10):
            await store.consume("apisports")
    warnings = [
        r.getMessage() for r in caplog.records if "provider_budget_warning" in r.getMessage()
    ]
    assert len(warnings) == 1
    assert "'used': 8" in warnings[0]
