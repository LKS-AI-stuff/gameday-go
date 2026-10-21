"""ORM models (TDD §7). Tables are added milestone by milestone."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    """One row per Supabase Auth user; `id` is the token's `sub` (TDD §6, §7.2)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    age_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # IANA zone; set from the device during onboarding (M1, BRD §7.1).
    timezone: Mapped[str | None] = mapped_column(Text)
    # "bounce" or "complaint" once the email provider reports one (FR-N6, M5).
    email_disabled_reason: Mapped[str | None] = mapped_column(Text)
