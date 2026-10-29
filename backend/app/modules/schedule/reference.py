"""Seeding reference data from `backend/data/` and API-Sports (TDD §7.1, FR-O1a)."""

import csv
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories import reference
from app.modules.schedule.centroids import DATA_DIR, PLACE_FILE, ZIP_FILE
from app.providers.apisports.base import ScheduleProvider

log = get_logger(__name__)

OVERRIDES_FILE = DATA_DIR / "reference_overrides.toml"
RIVALRIES_FILE = DATA_DIR / "rivalries.toml"
TEAM_OVERRIDE_FIELDS = frozenset(
    {"name", "nickname", "city", "state", "conference", "division", "home_venue_name"}
)


class ReferenceDataError(Exception):
    """Curated data or provider data is inconsistent; the message says what to fix."""


@dataclass(frozen=True)
class VenueCity:
    state: str | None = None
    country: str = "US"
    lat: float | None = None
    lng: float | None = None


@dataclass(frozen=True)
class Overrides:
    venue_cities: dict[str, VenueCity] = field(default_factory=dict)
    teams: dict[str, dict[str, Any]] = field(default_factory=dict)


def load_overrides(path: Path = OVERRIDES_FILE) -> Overrides:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    cities: dict[str, VenueCity] = {}
    for city, entry in data.get("venue_cities", {}).items():
        venue = VenueCity(
            state=entry.get("state"),
            country=entry.get("country", "US"),
            lat=entry.get("lat"),
            lng=entry.get("lng"),
        )
        if venue.country == "US" and not venue.state:
            raise ReferenceDataError(f"venue city {city!r}: US cities need a state")
        if venue.country != "US" and (venue.lat is None or venue.lng is None):
            raise ReferenceDataError(f"venue city {city!r}: non-US cities need lat and lng")
        cities[city] = venue
    teams: dict[str, dict[str, Any]] = {}
    for code, entry in data.get("teams", {}).items():
        unknown = set(entry) - TEAM_OVERRIDE_FIELDS
        if unknown:
            raise ReferenceDataError(f"team {code!r}: unknown override fields {sorted(unknown)}")
        teams[code] = dict(entry)
    return Overrides(cities, teams)


def load_rivalries(path: Path = RIVALRIES_FILE) -> list[tuple[str, str, str]]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    rows: list[tuple[str, str, str]] = []
    for entry in data.get("rivalry", []):
        teams = entry.get("teams", [])
        if len(teams) != 2 or teams[0] == teams[1] or not entry.get("reason"):
            raise ReferenceDataError(f"rivalry {entry!r}: needs two different teams and a reason")
        rows.append((teams[0], teams[1], entry["reason"]))
    return rows


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


async def seed_centroids(session: AsyncSession) -> tuple[int, int]:
    places = [
        (r["name"], r["state"], float(r["lat"]), float(r["lng"])) for r in _read_csv(PLACE_FILE)
    ]
    zips = [
        (r["zip"], float(r["lat"]), float(r["lng"]), r["place_name"], r["state"])
        for r in _read_csv(ZIP_FILE)
    ]
    await reference.upsert_places(session, places)
    await reference.upsert_zips(session, zips)
    return len(zips), len(places)


async def seed_teams(
    session: AsyncSession, provider: ScheduleProvider, season: int, overrides: Overrides
) -> int:
    """32 teams from API-Sports teams + standings (conference, division), then overrides.

    The home venue, state and coordinates are filled by the schedule sync from the games.
    Provider calls happen before any write; the caller commits.
    """
    teams = await provider.teams(season)
    standings = {s.provider_team_id: s for s in await provider.standings(season)}
    if len(standings) < len(teams):
        # Before a season starts its standings can be empty; divisions rarely change.
        standings = {s.provider_team_id: s for s in await provider.standings(season - 1)}
    count = 0
    for team in teams:
        standing = standings.get(team.provider_team_id)
        values: dict[str, Any] = {
            "id": team.code,
            "apisports_team_id": team.provider_team_id,
            "name": team.name,
            "nickname": team.name.split()[-1],  # every NFL nickname is one word
            "city": team.city,
            "conference": standing.conference if standing else None,
            "division": standing.division if standing else None,
        }
        values.update(overrides.teams.get(team.code, {}))
        if not values["conference"] or not values["division"]:
            raise ReferenceDataError(
                f"team {team.code}: no conference/division from standings; "
                f"add them under [teams.{team.code}] in reference_overrides.toml"
            )
        await reference.upsert_team(session, values)
        count += 1
    return count


async def seed_rivalries(session: AsyncSession) -> int:
    rows = load_rivalries()
    named = {t for a, b, _ in rows for t in (a, b)}
    missing = named - await reference.existing_team_ids(session, sorted(named))
    if missing:
        raise ReferenceDataError(f"rivalries.toml names unknown teams: {sorted(missing)}")
    await reference.replace_rivalries(session, rows)
    return len(rows)
