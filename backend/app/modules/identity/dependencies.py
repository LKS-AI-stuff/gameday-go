"""Auth dependencies for routers."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import TokenClaims, current_claims
from app.core.errors import ProblemError
from app.db.models import User
from app.db.session import get_session
from app.modules.identity import service

Session = Annotated[AsyncSession, Depends(get_session)]


async def current_user(
    claims: Annotated[TokenClaims, Depends(current_claims)], session: Session
) -> User:
    return await service.get_or_provision(session, claims)


async def confirmed_user(user: Annotated[User, Depends(current_user)]) -> User:
    """Data endpoints require the 18+ confirmation (FR-A3)."""
    if user.age_confirmed_at is None:
        raise ProblemError(403, "age_confirmation_required", "Confirm you are 18 or older")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
ConfirmedUser = Annotated[User, Depends(confirmed_user)]
