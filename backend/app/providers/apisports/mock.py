"""Fixture-backed schedule provider for automated tests and CI only (NFR-21)."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.domain.models import ProviderGame, ProviderStanding, ProviderTeam
from app.providers.apisports import mapping

FIXTURE_DIR = Path(__file__).resolve().parents[3] / "tests" / "contract" / "fixtures" / "apisports"


def load_fixture(name: str) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads((FIXTURE_DIR / f"{name}.json").read_text())
    return payload


class FixtureScheduleProvider:
    """Serves recorded payloads, or test-built variants, keyed by season."""

    def __init__(
        self,
        games: dict[int, dict[str, Any]],
        teams: dict[str, Any] | None = None,
        standings: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> None:
        self._games = games
        self._teams = teams or load_fixture("teams_2026")
        self._standings = standings or load_fixture("standings_2026")
        self._now = now
        self.calls: list[str] = []

    @classmethod
    def recorded(cls) -> "FixtureScheduleProvider":
        return cls({2026: load_fixture("games_2026")})

    async def games_for_season(self, season: int) -> list[ProviderGame]:
        self.calls.append(f"games_season:{season}")
        payload = self._games.get(season, {"response": []})
        return mapping.map_games(payload, season, self._now or datetime.now(UTC))

    async def teams(self, season: int) -> list[ProviderTeam]:
        self.calls.append(f"teams:{season}")
        return mapping.map_teams(self._teams)

    async def standings(self, season: int) -> list[ProviderStanding]:
        self.calls.append(f"standings:{season}")
        return mapping.map_standings(self._standings)
