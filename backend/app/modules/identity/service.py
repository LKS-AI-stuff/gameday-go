"""Current user, provisioning and age confirmation (BRD §8.1, TDD §6)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import TokenClaims
from app.db.models import User
from app.db.repositories import users


async def get_or_provision(session: AsyncSession, claims: TokenClaims) -> User:
    user = await users.get(session, claims.user_id)
    if user is not None:
        return user
    await users.create_if_missing(session, claims.user_id, claims.email, claims.age_confirmed)
    await session.commit()
    user = await users.get(session, claims.user_id)
    assert user is not None
    return user


async def confirm_age(session: AsyncSession, user: User) -> User:
    await users.confirm_age(session, user.id)
    await session.commit()
    await session.refresh(user)
    return user
