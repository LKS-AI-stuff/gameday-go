"""Atomic daily provider budgets in Postgres (TDD §8.2 step 2, FR-O4a).

Each consumption runs in its own short transaction, never inside a service transaction, so a
budget unit is spent exactly when a request is about to be sent.
"""

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.logging import get_logger
from app.core.settings import Provider, Settings

log = get_logger(__name__)


class BudgetExhausted(Exception):
    def __init__(self, provider: Provider) -> None:
        super().__init__(f"daily budget for {provider} is exhausted")
        self.provider = provider


@dataclass(frozen=True)
class BudgetState:
    used: int
    daily_limit: int
    reserved: int

    @property
    def remaining(self) -> int:
        return max(self.daily_limit - self.reserved - self.used, 0)


@dataclass(frozen=True)
class BudgetConfig:
    daily_limit: int
    reserve_pct: int

    @property
    def reserved(self) -> int:
        return math.ceil(self.daily_limit * self.reserve_pct / 100)


def budget_configs(settings: Settings) -> dict[Provider, BudgetConfig]:
    """Providers with a daily budget. Others arrive with their milestones (M2, M3)."""
    return {
        "apisports": BudgetConfig(settings.apisports_daily_budget, settings.apisports_reserve_pct)
    }


_ENSURE_ROW = text(
    """
    INSERT INTO app.provider_budgets (provider, day, daily_limit, used, reserved)
    VALUES (:provider, :day, :daily_limit, 0, :reserved)
    ON CONFLICT (provider, day) DO NOTHING
    """
)
_CONSUME = text(
    """
    UPDATE app.provider_budgets SET used = used + 1, updated_at = now()
    WHERE provider = :provider AND day = :day
      AND used < daily_limit - CASE WHEN :allow_reserved THEN 0 ELSE reserved END
    RETURNING used, daily_limit, reserved
    """
)


class BudgetStore:
    def __init__(self, engine: AsyncEngine, settings: Settings) -> None:
        self._engine = engine
        self._configs = budget_configs(settings)
        self._warn_pct = settings.provider_budget_warn_pct

    def is_budgeted(self, provider: Provider) -> bool:
        return provider in self._configs

    async def consume(
        self, provider: Provider, *, allow_reserved: bool = False, today: date | None = None
    ) -> BudgetState:
        config = self._configs[provider]
        day = today or datetime.now(UTC).date()  # API-Sports resets at 00:00 UTC
        params = {"provider": provider, "day": day}
        async with self._engine.begin() as conn:
            await conn.execute(
                _ENSURE_ROW,
                {**params, "daily_limit": config.daily_limit, "reserved": config.reserved},
            )
            row = (
                await conn.execute(_CONSUME, {**params, "allow_reserved": allow_reserved})
            ).first()
        if row is None:
            log.warning("provider_budget_exhausted", provider=provider, day=day.isoformat())
            raise BudgetExhausted(provider)
        state = BudgetState(used=row.used, daily_limit=row.daily_limit, reserved=row.reserved)
        threshold = math.ceil(state.daily_limit * self._warn_pct / 100)
        if state.used == threshold:
            log.warning(
                "provider_budget_warning",
                provider=provider,
                used=state.used,
                daily_limit=state.daily_limit,
                warn_pct=self._warn_pct,
            )
        return state
