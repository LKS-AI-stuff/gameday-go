"""User rows. Every method is keyed by the authenticated user's ID (FR-A5, TDD §5.3)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def get(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.scalar(select(User).where(User.id == user_id))


async def create_if_missing(
    session: AsyncSession, user_id: uuid.UUID, email: str, age_confirmed: bool
) -> None:
    """Insert the row on first authenticated request; concurrent first requests are safe."""
    await session.execute(
        insert(User)
        .values(
            id=user_id,
            email=email,
            age_confirmed_at=datetime.now(UTC) if age_confirmed else None,
        )
        .on_conflict_do_nothing(index_elements=[User.id])
    )


async def confirm_age(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Record the 18+ confirmation once; later calls keep the first timestamp."""
    await session.execute(
        update(User)
        .where(User.id == user_id, User.age_confirmed_at.is_(None))
        .values(age_confirmed_at=datetime.now(UTC))
    )


async def delete_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Removes the user and, through ON DELETE CASCADE, every user-owned row (FR-A4)."""
    await session.execute(delete(User).where(User.id == user_id))
