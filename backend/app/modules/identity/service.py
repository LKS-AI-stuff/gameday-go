"""Current user, provisioning and age confirmation (BRD §8.1, TDD §6)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import TokenClaims
from app.core.errors import ProblemError
from app.core.logging import get_logger
from app.core.redaction import hash_user_id
from app.core.supabase_admin import AuthAdminError, SupabaseAdmin
from app.db.models import User
from app.db.repositories import preferences, users

log = get_logger(__name__)


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


async def is_onboarded(session: AsyncSession, user: User) -> bool:
    return await preferences.exists(session, user.id)


async def delete_account(session: AsyncSession, admin: SupabaseAdmin, user: User) -> None:
    """Deletes all app data, then the sign-in account (FR-A4, TDD §6).

    App rows go first, in one transaction. If the auth deletion then fails, the client's retry
    re-provisions an empty row, deletes it and repeats the auth call, so it converges.
    """
    user_id = user.id
    await users.delete_user(session, user_id)
    await session.commit()
    try:
        await admin.delete_user(user_id)
    except AuthAdminError as exc:
        raise ProblemError(
            503, "auth_deletion_failed", "Your data was deleted, but sign-in removal failed"
        ) from exc
    log.info("account_deleted", user=hash_user_id(user_id))
