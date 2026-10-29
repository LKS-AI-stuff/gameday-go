"""Auth dependencies for routers."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import TokenClaims, current_claims
from app.core.errors import ProblemError
from app.core.rate_limits import RateLimits
from app.core.settings import Settings
from app.db.models import User
from app.db.session import get_session
from app.modules.identity import service

Session = Annotated[AsyncSession, Depends(get_session)]


async def current_user(
    claims: Annotated[TokenClaims, Depends(current_claims)], session: Session
) -> User:
    return await service.get_or_provision(session, claims)


async def user_rate_limit(request: Request, user: Annotated[User, Depends(current_user)]) -> None:
    """Per-user request limit on every authenticated route (NFR-15)."""
    limits: RateLimits = request.app.state.rate_limits
    limits.check_user(str(user.id))


async def ip_rate_limit(request: Request) -> None:
    """Per-IP request limit on unauthenticated routes (NFR-15)."""
    limits: RateLimits = request.app.state.rate_limits
    limits.check_ip(request)


async def confirmed_user(user: Annotated[User, Depends(current_user)]) -> User:
    """Data endpoints require the 18+ confirmation (FR-A3)."""
    if user.age_confirmed_at is None:
        raise ProblemError(403, "age_confirmation_required", "Confirm you are 18 or older")
    return user


def app_settings(request: Request) -> Settings:
    """The settings the app was created with (tests pass their own)."""
    settings: Settings = request.app.state.settings
    return settings


AppSettings = Annotated[Settings, Depends(app_settings)]
CurrentUser = Annotated[User, Depends(current_user)]
ConfirmedUser = Annotated[User, Depends(confirmed_user)]
