"""users table and RLS on the migration version table

Revision ID: 0001
Revises:
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from migrations.hardening import secure_table

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Alembic creates app.alembic_version itself; it gets the same protection.
    secure_table("alembic_version")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("age_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone", sa.Text(), nullable=True),
        sa.Column("email_disabled_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        schema="app",
    )
    secure_table("users")


def downgrade() -> None:
    op.drop_table("users", schema="app")
    op.execute("DROP POLICY IF EXISTS backend_all ON app.alembic_version")
    op.execute("ALTER TABLE app.alembic_version NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE app.alembic_version DISABLE ROW LEVEL SECURITY")
