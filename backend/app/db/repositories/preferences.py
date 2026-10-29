"""User preferences, favorite teams and notification settings (TDD §7.2).

Every function takes the authenticated user's ID and filters by it (FR-A5, TDD §5.3).
"""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    NOTIFICATION_CATEGORIES,
    NotificationSetting,
    UserFavoriteTeam,
    UserPreferences,
)


async def get(session: AsyncSession, user_id: uuid.UUID) -> UserPreferences | None:
    return await session.scalar(select(UserPreferences).where(UserPreferences.user_id == user_id))


async def exists(session: AsyncSession, user_id: uuid.UUID) -> bool:
    found = await session.scalar(
        select(UserPreferences.user_id).where(UserPreferences.user_id == user_id)
    )
    return found is not None


async def upsert(session: AsyncSession, user_id: uuid.UUID, values: dict[str, Any]) -> None:
    stmt = insert(UserPreferences).values(user_id=user_id, **values)
    await session.execute(
        stmt.on_conflict_do_update(
            index_elements=[UserPreferences.user_id], set_={**values, "updated_at": func.now()}
        )
    )


async def favorite_team_ids(session: AsyncSession, user_id: uuid.UUID) -> list[str]:
    rows = await session.scalars(
        select(UserFavoriteTeam.team_id)
        .where(UserFavoriteTeam.user_id == user_id)
        .order_by(UserFavoriteTeam.team_id)
    )
    return list(rows)


async def replace_favorites(
    session: AsyncSession, user_id: uuid.UUID, team_ids: Sequence[str]
) -> None:
    await session.execute(delete(UserFavoriteTeam).where(UserFavoriteTeam.user_id == user_id))
    for team_id in team_ids:
        session.add(UserFavoriteTeam(user_id=user_id, team_id=team_id))


async def ensure_notification_settings(session: AsyncSession, user_id: uuid.UUID) -> None:
    """All four categories, email on, unless the user already has rows."""
    stmt = insert(NotificationSetting).values(
        [
            {"user_id": user_id, "category": c, "email_enabled": True}
            for c in NOTIFICATION_CATEGORIES
        ]
    )
    await session.execute(stmt.on_conflict_do_nothing())


async def notification_settings(session: AsyncSession, user_id: uuid.UUID) -> dict[str, bool]:
    rows = await session.scalars(
        select(NotificationSetting).where(NotificationSetting.user_id == user_id)
    )
    return {row.category: row.email_enabled for row in rows}


async def set_notification_settings(
    session: AsyncSession, user_id: uuid.UUID, categories: dict[str, bool]
) -> None:
    stmt = insert(NotificationSetting).values(
        [{"user_id": user_id, "category": c, "email_enabled": on} for c, on in categories.items()]
    )
    await session.execute(
        stmt.on_conflict_do_update(
            index_elements=[NotificationSetting.user_id, NotificationSetting.category],
            set_={"email_enabled": stmt.excluded.email_enabled, "updated_at": func.now()},
        )
    )


async def set_notification_level(session: AsyncSession, user_id: uuid.UUID, level: str) -> None:
    prefs = await get(session, user_id)
    if prefs is not None:
        prefs.notification_level = level
