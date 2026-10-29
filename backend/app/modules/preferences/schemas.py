"""Preference API shapes (BRD §7.1, P1-P6). Only these fields are accepted (AC-1)."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Travel = Literal["low", "medium", "high"]
Spending = Literal["less", "medium", "more"]
Viewing = Literal["stadium", "bar", "home", "flexible"]
NotificationLevel = Literal["off", "low", "medium", "high"]
Zip = Annotated[str, Field(pattern=r"^\d{5}$")]
TeamId = Annotated[str, Field(min_length=1, max_length=8)]


class PreferencesIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    favorite_team_ids: Annotated[list[TeamId], Field(min_length=1, max_length=32)]
    home_zip: Zip
    travel: Travel
    spending: Spending
    max_ticket_price_usd: Annotated[int, Field(ge=1, le=5000)] | None = None
    viewing: Viewing
    notification_level: NotificationLevel
    timezone: Annotated[str, Field(min_length=1, max_length=64)]


class Place(BaseModel):
    place_name: str
    state: str


class Preferences(BaseModel):
    favorite_team_ids: list[str]
    home_zip: str
    home_place: Place | None
    travel: Travel
    spending: Spending
    max_ticket_price_usd: int | None
    viewing: Viewing
    notification_level: NotificationLevel
    timezone: str | None


class NotificationCategories(BaseModel):
    model_config = ConfigDict(extra="forbid")

    watch_hit: bool
    schedule_change: bool
    reminder: bool
    digest: bool


class NotificationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: NotificationLevel
    categories: NotificationCategories


class ZipInfo(BaseModel):
    zip: str
    place_name: str
    state: str


class Coordinates(BaseModel):
    """Device position for "Use my location". Used for this request only, never stored."""

    model_config = ConfigDict(extra="forbid")

    lat: Annotated[float, Field(ge=-90, le=90)]
    lng: Annotated[float, Field(ge=-180, le=180)]
