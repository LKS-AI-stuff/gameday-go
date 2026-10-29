"""Schedule API shapes (FR-SC1-SC5, FR-SC8, FR-O1c). Times are UTC ISO-8601 (NFR-4)."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

Weight = Literal["high", "medium", "info"]
PlanningState = Literal["open", "opens_on", "closed"]
SOURCE = "API-Sports"


class Team(BaseModel):
    id: str
    name: str
    nickname: str
    city: str
    conference: str
    division: str


class TeamRef(BaseModel):
    id: str
    nickname: str
    name: str


class GameTag(BaseModel):
    tag: str
    weight: Weight
    detail: str | None = None


class Planning(BaseModel):
    status: PlanningState
    opens_at: datetime | None = None


class WeekOption(BaseModel):
    week: int
    label: str


class Season(BaseModel):
    year: int
    status: Literal["upcoming", "active", "completed"]
    schedule_available: bool
    current_week: int | None
    weeks: list[WeekOption]
    planning_window_days: int
    schedule_updated_at: datetime | None
    source: str = SOURCE


class GameSummary(BaseModel):
    id: uuid.UUID
    season: int
    week: int
    week_label: str
    stage: Literal["regular", "playoff"]
    game_date: date | None
    kickoff_at: datetime | None
    kickoff_tbd: bool
    home: TeamRef | None
    away: TeamRef | None
    home_placeholder: str | None
    away_placeholder: str | None
    venue_name: str | None
    venue_city: str | None
    venue_state: str | None
    venue_country: str | None
    status: str
    tags: list[GameTag]
    planning: Planning
    distance_mi: float | None
    is_favorite: bool
    is_sample: bool


class GamePage(BaseModel):
    items: list[GameSummary]
    next_cursor: str | None


class Source(BaseModel):
    provider: str = SOURCE
    schedule_updated_at: datetime | None
    game_synced_at: datetime


class GameDetail(GameSummary):
    source: Source
    travel_hint: Literal["outside_travel_area"] | None
