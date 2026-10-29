from typing import Annotated

from fastapi import APIRouter, Path

from app.modules.identity.dependencies import ConfirmedUser, Session
from app.modules.preferences import service
from app.modules.preferences.schemas import (
    Coordinates,
    NotificationSettings,
    Preferences,
    PreferencesIn,
    ZipInfo,
)

router = APIRouter(tags=["preferences"])


@router.get("/me/preferences", operation_id="getPreferences")
async def get_preferences(user: ConfirmedUser, session: Session) -> Preferences:
    return await service.get_preferences(session, user)


@router.put("/me/preferences", operation_id="putPreferences")
async def put_preferences(
    body: PreferencesIn, user: ConfirmedUser, session: Session
) -> Preferences:
    """Onboarding (P1-P6 plus the device time zone) and later edits from Settings (FR-P1, FR-P2)."""
    return await service.save_preferences(session, user, body)


@router.get("/me/notification-settings", operation_id="getNotificationSettings")
async def get_notification_settings(user: ConfirmedUser, session: Session) -> NotificationSettings:
    return await service.get_notification_settings(session, user)


@router.put("/me/notification-settings", operation_id="putNotificationSettings")
async def put_notification_settings(
    body: NotificationSettings, user: ConfirmedUser, session: Session
) -> NotificationSettings:
    return await service.save_notification_settings(session, user, body)


@router.get("/zip/{zip_code}", operation_id="getZip")
async def get_zip(
    zip_code: Annotated[str, Path(pattern=r"^\d{5}$")], user: ConfirmedUser, session: Session
) -> ZipInfo:
    del user
    return await service.lookup_zip(session, zip_code)


@router.post("/zip/nearest", operation_id="nearestZip")
async def nearest_zip(body: Coordinates, user: ConfirmedUser, session: Session) -> ZipInfo:
    """Nearest ZIP for "Use my location". Coordinates travel in the body, never in URLs."""
    del user
    return await service.nearest(session, body)
