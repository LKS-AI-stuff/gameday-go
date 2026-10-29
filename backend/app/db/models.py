"""ORM models (TDD §7). Tables are added milestone by milestone."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _one_of(column: str, values: tuple[str, ...], name: str) -> CheckConstraint:
    allowed = ", ".join(f"'{v}'" for v in values)
    return CheckConstraint(f"{column} IN ({allowed})", name=name)


TRAVEL = ("low", "medium", "high")
SPENDING = ("less", "medium", "more")
VIEWING = ("stadium", "bar", "home", "flexible")
NOTIFICATION_LEVELS = ("off", "low", "medium", "high")
NOTIFICATION_CATEGORIES = ("watch_hit", "schedule_change", "reminder", "digest")
GAME_STATUSES = (
    "scheduled",
    "in_progress",
    "halftime",
    "final",
    "final_ot",
    "postponed",
    "cancelled",
)
PLATFORMS = ("ios", "android", "web")


class User(TimestampMixin, Base):
    """One row per Supabase Auth user; `id` is the token's `sub` (TDD §6, §7.2)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    age_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # IANA zone; set from the device during onboarding (BRD §7.1).
    timezone: Mapped[str | None] = mapped_column(Text)
    # "bounce" or "complaint" once the email provider reports one (FR-N6, M5).
    email_disabled_reason: Mapped[str | None] = mapped_column(Text)


# ---- Reference data (TDD §7.1)


class Team(TimestampMixin, Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(Text, primary_key=True)  # provider team code, e.g. "CHI"
    apisports_team_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)  # "Chicago Bears"
    nickname: Mapped[str] = mapped_column(Text, nullable=False)  # "Bears"
    city: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str | None] = mapped_column(Text)
    conference: Mapped[str] = mapped_column(Text, nullable=False)  # AFC / NFC
    division: Mapped[str] = mapped_column(Text, nullable=False)  # East / North / South / West
    home_venue_name: Mapped[str | None] = mapped_column(Text)
    home_venue_lat: Mapped[float | None] = mapped_column(Float)
    home_venue_lng: Mapped[float | None] = mapped_column(Float)
    ticketmaster_attraction_id: Mapped[str | None] = mapped_column(Text)


class VenueRef(TimestampMixin, Base):
    __tablename__ = "venues_ref"
    # NULLS NOT DISTINCT: a venue with no city is still one row, not one per sync.
    __table_args__ = (
        UniqueConstraint(
            "name", "city", name="uq_venues_ref_name_city", postgresql_nulls_not_distinct=True
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(Text)  # ISO 3166-1 alpha-2
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(Text, nullable=False)  # place_centroids / override / none


class FeaturedRivalry(TimestampMixin, Base):
    __tablename__ = "featured_rivalries"
    __table_args__ = (
        PrimaryKeyConstraint("team_a", "team_b"),
        CheckConstraint("team_a < team_b", name="unordered_pair"),
    )

    team_a: Mapped[str] = mapped_column(Text, ForeignKey("teams.id"))
    team_b: Mapped[str] = mapped_column(Text, ForeignKey("teams.id"))
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class ZipCentroid(TimestampMixin, Base):
    __tablename__ = "zip_centroids"
    __table_args__ = (Index("ix_zip_centroids_lat", "lat"),)

    zip: Mapped[str] = mapped_column(Text, primary_key=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    place_name: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False)


class PlaceCentroid(TimestampMixin, Base):
    __tablename__ = "place_centroids"
    __table_args__ = (PrimaryKeyConstraint("name", "state"),)

    name: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(Text)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)


# ---- Preferences (TDD §7.2)


class UserPreferences(TimestampMixin, Base):
    __tablename__ = "user_preferences"
    __table_args__ = (
        _one_of("travel", TRAVEL, "travel"),
        _one_of("spending", SPENDING, "spending"),
        _one_of("viewing", VIEWING, "viewing"),
        _one_of("notification_level", NOTIFICATION_LEVELS, "notification_level"),
        CheckConstraint("max_ticket_price_cents > 0", name="max_ticket_price_positive"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    home_zip: Mapped[str] = mapped_column(Text, nullable=False)
    travel: Mapped[str] = mapped_column(Text, nullable=False)
    spending: Mapped[str] = mapped_column(Text, nullable=False)
    max_ticket_price_cents: Mapped[int | None] = mapped_column(Integer)
    viewing: Mapped[str] = mapped_column(Text, nullable=False)
    notification_level: Mapped[str] = mapped_column(Text, nullable=False)


class UserFavoriteTeam(TimestampMixin, Base):
    __tablename__ = "user_favorite_teams"
    __table_args__ = (PrimaryKeyConstraint("user_id", "team_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    team_id: Mapped[str] = mapped_column(Text, ForeignKey("teams.id"))


class NotificationSetting(TimestampMixin, Base):
    __tablename__ = "notification_settings"
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "category"),
        _one_of("category", NOTIFICATION_CATEGORIES, "category"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    category: Mapped[str] = mapped_column(Text)
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


# ---- Schedule (TDD §7.3)


class Game(TimestampMixin, Base):
    __tablename__ = "games"
    __table_args__ = (
        _one_of("stage", ("regular", "playoff"), "stage"),
        _one_of("status", GAME_STATUSES, "status"),
        Index("ix_games_season_week", "season", "week"),
        Index("ix_games_kickoff_at", "kickoff_at"),
        Index("ix_games_sort_at", "sort_at", "id"),
        Index("ix_games_home_team_id", "home_team_id"),
        Index("ix_games_away_team_id", "away_team_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    apisports_game_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    # 1-18 regular season; 19-22 Wild Card, Divisional, Conference, Super Bowl.
    week: Mapped[int] = mapped_column(Integer, nullable=False)
    stage: Mapped[str] = mapped_column(Text, nullable=False)
    home_team_id: Mapped[str | None] = mapped_column(Text, ForeignKey("teams.id"))
    away_team_id: Mapped[str | None] = mapped_column(Text, ForeignKey("teams.id"))
    home_placeholder: Mapped[str | None] = mapped_column(Text)
    away_placeholder: Mapped[str | None] = mapped_column(Text)
    # Calendar date of the game (US Eastern); kept when the kickoff time is TBD.
    game_date: Mapped[date | None] = mapped_column(Date)
    kickoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    kickoff_tbd: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Ordering key: kickoff, or 23:59 Eastern on the game day while TBD (lists and cursors).
    sort_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    venue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("venues_ref.id")
    )
    venue_name: Mapped[str | None] = mapped_column(Text)
    venue_city: Mapped[str | None] = mapped_column(Text)
    venue_state: Mapped[str | None] = mapped_column(Text)
    venue_country: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="scheduled")
    # Live state arrives in M4 (TD2).
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    quarter: Mapped[str | None] = mapped_column(Text)
    clock: Mapped[str | None] = mapped_column(Text)
    score_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_sample: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Season(TimestampMixin, Base):
    __tablename__ = "seasons"
    __table_args__ = (_one_of("status", ("upcoming", "active", "completed"), "status"),)

    year: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    schedule_available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    super_bowl_game_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id", ondelete="SET NULL")
    )


class SyncRun(TimestampMixin, Base):
    __tablename__ = "sync_runs"
    __table_args__ = (
        _one_of("kind", ("schedule", "standings"), "kind"),
        _one_of("status", ("running", "succeeded", "failed"), "status"),
        Index("ix_sync_runs_kind_started_at", "kind", "started_at"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    season: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False)
    records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    changes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text)


class GameChange(TimestampMixin, Base):
    __tablename__ = "game_changes"
    __table_args__ = (Index("ix_game_changes_game_id", "game_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), nullable=False
    )
    field: Mapped[str] = mapped_column(Text, nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sync_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sync_runs.id", ondelete="CASCADE"), nullable=False
    )


class GameTag(TimestampMixin, Base):
    __tablename__ = "game_tags"
    __table_args__ = (
        PrimaryKeyConstraint("game_id", "tag"),
        _one_of("weight", ("high", "medium", "info"), "weight"),
        _one_of("source", ("schedule", "standings"), "source"),
    )

    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE")
    )
    tag: Mapped[str] = mapped_column(Text)
    weight: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ---- Operations (TDD §7.6)


class ProviderBudget(TimestampMixin, Base):
    __tablename__ = "provider_budgets"
    __table_args__ = (PrimaryKeyConstraint("provider", "day"),)

    provider: Mapped[str] = mapped_column(Text)
    day: Mapped[date] = mapped_column(Date)  # UTC
    daily_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AppEvent(TimestampMixin, Base):
    __tablename__ = "app_events"
    __table_args__ = (
        _one_of("platform", PLATFORMS, "platform"),
        Index("ix_app_events_name_received_at", "name", "received_at"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    props: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    client_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
