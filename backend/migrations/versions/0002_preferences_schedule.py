"""M1 tables: reference data, preferences, schedule and operations (TDD §7.1-7.3, §7.6)

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-29 00:01:14.349605
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from migrations.hardening import secure_table

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "place_centroids",
    "provider_budgets",
    "sync_runs",
    "teams",
    "venues_ref",
    "zip_centroids",
    "app_events",
    "featured_rivalries",
    "games",
    "notification_settings",
    "user_favorite_teams",
    "user_preferences",
    "game_changes",
    "game_tags",
    "seasons",
)


def upgrade() -> None:
    op.create_table(
        "place_centroids",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("name", "state", name=op.f("pk_place_centroids")),
        schema="app",
    )
    op.create_table(
        "provider_budgets",
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("daily_limit", sa.Integer(), nullable=False),
        sa.Column("used", sa.Integer(), nullable=False),
        sa.Column("reserved", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("provider", "day", name=op.f("pk_provider_budgets")),
        schema="app",
    )
    op.create_table(
        "sync_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("records", sa.Integer(), nullable=False),
        sa.Column("changes", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("kind IN ('schedule', 'standings')", name=op.f("ck_sync_runs_kind")),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')", name=op.f("ck_sync_runs_status")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sync_runs")),
        schema="app",
    )
    op.create_index(
        "ix_sync_runs_kind_started_at",
        "sync_runs",
        ["kind", "started_at"],
        unique=False,
        schema="app",
    )
    op.create_table(
        "teams",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("apisports_team_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("nickname", sa.Text(), nullable=False),
        sa.Column("city", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("conference", sa.Text(), nullable=False),
        sa.Column("division", sa.Text(), nullable=False),
        sa.Column("home_venue_name", sa.Text(), nullable=True),
        sa.Column("home_venue_lat", sa.Float(), nullable=True),
        sa.Column("home_venue_lng", sa.Float(), nullable=True),
        sa.Column("ticketmaster_attraction_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teams")),
        sa.UniqueConstraint("apisports_team_id", name=op.f("uq_teams_apisports_team_id")),
        schema="app",
    )
    op.create_table(
        "venues_ref",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_venues_ref")),
        sa.UniqueConstraint(
            "name", "city", name="uq_venues_ref_name_city", postgresql_nulls_not_distinct=True
        ),
        schema="app",
    )
    op.create_table(
        "zip_centroids",
        sa.Column("zip", sa.Text(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("place_name", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("zip", name=op.f("pk_zip_centroids")),
        schema="app",
    )
    op.create_index("ix_zip_centroids_lat", "zip_centroids", ["lat"], unique=False, schema="app")
    op.create_table(
        "app_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "props",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("client_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "platform IN ('ios', 'android', 'web')", name=op.f("ck_app_events_platform")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app.users.id"],
            name=op.f("fk_app_events_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_app_events")),
        schema="app",
    )
    op.create_index(
        "ix_app_events_name_received_at",
        "app_events",
        ["name", "received_at"],
        unique=False,
        schema="app",
    )
    op.create_table(
        "featured_rivalries",
        sa.Column("team_a", sa.Text(), nullable=False),
        sa.Column("team_b", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("team_a < team_b", name=op.f("ck_featured_rivalries_unordered_pair")),
        sa.ForeignKeyConstraint(
            ["team_a"], ["app.teams.id"], name=op.f("fk_featured_rivalries_team_a_teams")
        ),
        sa.ForeignKeyConstraint(
            ["team_b"], ["app.teams.id"], name=op.f("fk_featured_rivalries_team_b_teams")
        ),
        sa.PrimaryKeyConstraint("team_a", "team_b", name=op.f("pk_featured_rivalries")),
        schema="app",
    )
    op.create_table(
        "games",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("apisports_game_id", sa.Text(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("week", sa.Integer(), nullable=False),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("home_team_id", sa.Text(), nullable=True),
        sa.Column("away_team_id", sa.Text(), nullable=True),
        sa.Column("home_placeholder", sa.Text(), nullable=True),
        sa.Column("away_placeholder", sa.Text(), nullable=True),
        sa.Column("game_date", sa.Date(), nullable=True),
        sa.Column("kickoff_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("kickoff_tbd", sa.Boolean(), nullable=False),
        sa.Column("sort_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("venue_id", sa.UUID(), nullable=True),
        sa.Column("venue_name", sa.Text(), nullable=True),
        sa.Column("venue_city", sa.Text(), nullable=True),
        sa.Column("venue_state", sa.Text(), nullable=True),
        sa.Column("venue_country", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default="scheduled", nullable=False),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("quarter", sa.Text(), nullable=True),
        sa.Column("clock", sa.Text(), nullable=True),
        sa.Column("score_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_sample", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("stage IN ('regular', 'playoff')", name=op.f("ck_games_stage")),
        sa.CheckConstraint(
            "status IN ('scheduled', 'in_progress', 'halftime', 'final', 'final_ot', "
            "'postponed', 'cancelled')",
            name=op.f("ck_games_status"),
        ),
        sa.ForeignKeyConstraint(
            ["away_team_id"], ["app.teams.id"], name=op.f("fk_games_away_team_id_teams")
        ),
        sa.ForeignKeyConstraint(
            ["home_team_id"], ["app.teams.id"], name=op.f("fk_games_home_team_id_teams")
        ),
        sa.ForeignKeyConstraint(
            ["venue_id"], ["app.venues_ref.id"], name=op.f("fk_games_venue_id_venues_ref")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_games")),
        sa.UniqueConstraint("apisports_game_id", name=op.f("uq_games_apisports_game_id")),
        schema="app",
    )
    op.create_index("ix_games_away_team_id", "games", ["away_team_id"], unique=False, schema="app")
    op.create_index("ix_games_home_team_id", "games", ["home_team_id"], unique=False, schema="app")
    op.create_index("ix_games_kickoff_at", "games", ["kickoff_at"], unique=False, schema="app")
    op.create_index("ix_games_sort_at", "games", ["sort_at", "id"], unique=False, schema="app")
    op.create_index("ix_games_season_week", "games", ["season", "week"], unique=False, schema="app")
    op.create_table(
        "notification_settings",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "category IN ('watch_hit', 'schedule_change', 'reminder', 'digest')",
            name=op.f("ck_notification_settings_category"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app.users.id"],
            name=op.f("fk_notification_settings_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "category", name=op.f("pk_notification_settings")),
        schema="app",
    )
    op.create_table(
        "user_favorite_teams",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("team_id", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["app.teams.id"], name=op.f("fk_user_favorite_teams_team_id_teams")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app.users.id"],
            name=op.f("fk_user_favorite_teams_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "team_id", name=op.f("pk_user_favorite_teams")),
        schema="app",
    )
    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("home_zip", sa.Text(), nullable=False),
        sa.Column("travel", sa.Text(), nullable=False),
        sa.Column("spending", sa.Text(), nullable=False),
        sa.Column("max_ticket_price_cents", sa.Integer(), nullable=True),
        sa.Column("viewing", sa.Text(), nullable=False),
        sa.Column("notification_level", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "notification_level IN ('off', 'low', 'medium', 'high')",
            name=op.f("ck_user_preferences_notification_level"),
        ),
        sa.CheckConstraint(
            "spending IN ('less', 'medium', 'more')", name=op.f("ck_user_preferences_spending")
        ),
        sa.CheckConstraint(
            "travel IN ('low', 'medium', 'high')", name=op.f("ck_user_preferences_travel")
        ),
        sa.CheckConstraint(
            "viewing IN ('stadium', 'bar', 'home', 'flexible')",
            name=op.f("ck_user_preferences_viewing"),
        ),
        sa.CheckConstraint(
            "max_ticket_price_cents > 0", name=op.f("ck_user_preferences_max_ticket_price_positive")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app.users.id"],
            name=op.f("fk_user_preferences_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_user_preferences")),
        schema="app",
    )
    op.create_table(
        "game_changes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("game_id", sa.UUID(), nullable=False),
        sa.Column("field", sa.Text(), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sync_run_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["app.games.id"],
            name=op.f("fk_game_changes_game_id_games"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sync_run_id"],
            ["app.sync_runs.id"],
            name=op.f("fk_game_changes_sync_run_id_sync_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_game_changes")),
        schema="app",
    )
    op.create_index(
        "ix_game_changes_game_id", "game_changes", ["game_id"], unique=False, schema="app"
    )
    op.create_table(
        "game_tags",
        sa.Column("game_id", sa.UUID(), nullable=False),
        sa.Column("tag", sa.Text(), nullable=False),
        sa.Column("weight", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("source IN ('schedule', 'standings')", name=op.f("ck_game_tags_source")),
        sa.CheckConstraint(
            "weight IN ('high', 'medium', 'info')", name=op.f("ck_game_tags_weight")
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["app.games.id"],
            name=op.f("fk_game_tags_game_id_games"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("game_id", "tag", name=op.f("pk_game_tags")),
        schema="app",
    )
    op.create_table(
        "seasons",
        sa.Column("year", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("schedule_available_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("super_bowl_game_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('upcoming', 'active', 'completed')", name=op.f("ck_seasons_status")
        ),
        sa.ForeignKeyConstraint(
            ["super_bowl_game_id"],
            ["app.games.id"],
            name=op.f("fk_seasons_super_bowl_game_id_games"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("year", name=op.f("pk_seasons")),
        schema="app",
    )
    # Every new table gets forced RLS and the backend-only policy (TDD §6.1).
    for table in TABLES:
        secure_table(table)
    # Call secure_table("<name>") for every table created above (TDD §6.1).


def downgrade() -> None:
    op.drop_table("seasons", schema="app")
    op.drop_table("game_tags", schema="app")
    op.drop_index("ix_game_changes_game_id", table_name="game_changes", schema="app")
    op.drop_table("game_changes", schema="app")
    op.drop_table("user_preferences", schema="app")
    op.drop_table("user_favorite_teams", schema="app")
    op.drop_table("notification_settings", schema="app")
    op.drop_index("ix_games_season_week", table_name="games", schema="app")
    op.drop_index("ix_games_sort_at", table_name="games", schema="app")
    op.drop_index("ix_games_kickoff_at", table_name="games", schema="app")
    op.drop_index("ix_games_home_team_id", table_name="games", schema="app")
    op.drop_index("ix_games_away_team_id", table_name="games", schema="app")
    op.drop_table("games", schema="app")
    op.drop_table("featured_rivalries", schema="app")
    op.drop_index("ix_app_events_name_received_at", table_name="app_events", schema="app")
    op.drop_table("app_events", schema="app")
    op.drop_index("ix_zip_centroids_lat", table_name="zip_centroids", schema="app")
    op.drop_table("zip_centroids", schema="app")
    op.drop_table("venues_ref", schema="app")
    op.drop_table("teams", schema="app")
    op.drop_index("ix_sync_runs_kind_started_at", table_name="sync_runs", schema="app")
    op.drop_table("sync_runs", schema="app")
    op.drop_table("provider_budgets", schema="app")
    op.drop_table("place_centroids", schema="app")
