"""Schedule provider interface (TDD §8.1). M4 adds `games_on_date` for score polling."""

from typing import Protocol

from app.domain.models import ProviderGame, ProviderStanding, ProviderTeam


class ScheduleProvider(Protocol):
    async def games_for_season(self, season: int) -> list[ProviderGame]: ...

    async def teams(self, season: int) -> list[ProviderTeam]: ...

    async def standings(self, season: int) -> list[ProviderStanding]: ...
