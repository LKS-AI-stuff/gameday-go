"""Live API-Sports adapter. Every call goes through `ProviderClient` (TDD §8.2)."""

from datetime import UTC, datetime
from typing import Any

from app.core.http import ProviderClient
from app.core.settings import Settings
from app.domain.models import ProviderGame, ProviderStanding, ProviderTeam
from app.providers.apisports import mapping
from app.providers.errors import ProviderError


class ApiSportsProvider:
    def __init__(self, client: ProviderClient, settings: Settings) -> None:
        # Settings require the key whenever the provider is enabled; when it's switched off,
        # ProviderClient raises ProviderDisabled before anything is sent (FR-O5).
        self._client = client
        self._base = settings.apisports_base_url.rstrip("/")
        self._league = settings.apisports_league_id
        self._key = settings.apisports_key

    async def _get(self, path: str, endpoint: str, season: int) -> dict[str, Any]:
        response = await self._client.request(
            "apisports",
            "GET",
            f"{self._base}{path}",
            endpoint=endpoint,
            params={"league": self._league, "season": season},
            headers={"x-apisports-key": self._key.get_secret_value() if self._key else ""},
        )
        if response.status_code != 200:
            raise ProviderError("apisports", endpoint, response.status_code)
        payload: dict[str, Any] = response.json()
        if mapping.provider_errors(payload):
            # Error detail can name the plan; log only the field names.
            raise ProviderError("apisports", endpoint, response.status_code)
        return payload

    async def games_for_season(self, season: int) -> list[ProviderGame]:
        payload = await self._get("/games", "games_season", season)
        return mapping.map_games(payload, season, datetime.now(UTC))

    async def teams(self, season: int) -> list[ProviderTeam]:
        return mapping.map_teams(await self._get("/teams", "teams", season))

    async def standings(self, season: int) -> list[ProviderStanding]:
        return mapping.map_standings(await self._get("/standings", "standings", season))
