from fastapi import APIRouter, Request, Response

from app.core.supabase_admin import SupabaseAdmin
from app.modules.identity import service
from app.modules.identity.dependencies import CurrentUser, Session
from app.modules.identity.schemas import Me

router = APIRouter(prefix="/me", tags=["identity"])


@router.get("", operation_id="getMe")
async def get_me(user: CurrentUser, session: Session) -> Me:
    return Me.from_user(user, await service.is_onboarded(session, user))


@router.delete(
    "",
    operation_id="deleteMe",
    status_code=204,
    response_class=Response,
    responses={503: {"description": "Data deleted; sign-in removal failed (retry)"}},
)
async def delete_me(request: Request, user: CurrentUser, session: Session) -> Response:
    """Delete the account and all its data (FR-A4)."""
    admin: SupabaseAdmin = request.app.state.supabase_admin
    await service.delete_account(session, admin, user)
    return Response(status_code=204)


@router.post("/age-confirmation", operation_id="confirmAge")
async def confirm_age(user: CurrentUser, session: Session) -> Me:
    """Record the 18+ confirmation (FR-A3). Used after social sign-in (M6)."""
    user = await service.confirm_age(session, user)
    return Me.from_user(user, await service.is_onboarded(session, user))
