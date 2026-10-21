from fastapi import APIRouter

from app.modules.identity import service
from app.modules.identity.dependencies import CurrentUser, Session
from app.modules.identity.schemas import Me

router = APIRouter(prefix="/me", tags=["identity"])


@router.get("", operation_id="getMe")
async def get_me(user: CurrentUser) -> Me:
    return Me.from_user(user)


@router.post("/age-confirmation", operation_id="confirmAge")
async def confirm_age(user: CurrentUser, session: Session) -> Me:
    """Record the 18+ confirmation (FR-A3). Used after social sign-in (M6)."""
    return Me.from_user(await service.confirm_age(session, user))
