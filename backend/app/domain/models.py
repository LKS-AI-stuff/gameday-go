"""Contracts between adapters, rules and services (TDD §11.7). Pure: no I/O."""

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


class GameStatus(StrEnum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    HALFTIME = "halftime"
    FINAL = "final"
    FINAL_OT = "final_ot"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


FINISHED_STATUSES = frozenset({GameStatus.FINAL, GameStatus.FINAL_OT, GameStatus.CANCELLED})

Stage = Literal["regular", "playoff"]

# Playoff rounds are stored as weeks after the 18-week regular season.
WILD_CARD_WEEK = 19
DIVISIONAL_WEEK = 20
CONFERENCE_WEEK = 21
SUPER_BOWL_WEEK = 22


@dataclass(frozen=True)
class LatLng:
    lat: float
    lng: float


class Provenance(BaseModel):
    provider: Literal["apisports", "ticketmaster", "google_places", "gamedaygo"]
    retrieved_at: datetime  # UTC
    is_sample: bool = False


# ---- Provider-normalized types (adapters return these; raw payloads never leave the adapter)


class ProviderTeamRef(BaseModel):
    provider_team_id: str
    name: str


class ProviderGame(BaseModel):
    provider_game_id: str
    season: int
    week: int
    stage: Stage
    game_date: date | None
    kickoff_at: datetime | None  # None when TBD
    kickoff_tbd: bool
    home: ProviderTeamRef | None  # None while playoff teams are TBD
    away: ProviderTeamRef | None
    venue_name: str | None
    venue_city: str | None
    status: GameStatus
    provenance: Provenance


class ProviderTeam(BaseModel):
    provider_team_id: str
    code: str
    name: str
    city: str


class ProviderStanding(BaseModel):
    provider_team_id: str
    conference: str  # "AFC" / "NFC"
    division: str  # "East" / "North" / "South" / "West"


# ---- Rule inputs


@dataclass(frozen=True)
class TeamFacts:
    id: str
    conference: str
    division: str


@dataclass(frozen=True)
class GameFacts:
    id: uuid.UUID
    season: int
    week: int
    stage: Stage
    home_team_id: str | None
    away_team_id: str | None
    game_date: date | None
    kickoff_at: datetime | None
    venue_country: str | None


TagWeight = Literal["high", "medium", "info"]


@dataclass(frozen=True)
class Tag:
    tag: str
    weight: TagWeight
    detail: str | None = None
