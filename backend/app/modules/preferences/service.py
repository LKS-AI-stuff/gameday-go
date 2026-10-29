"""Preferences, notification settings and ZIP lookup (BRD §7.1, §8.2; FR-P1-P4, BR-N9)."""

from zoneinfo import available_timezones

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ProblemError
from app.db.models import User
from app.db.repositories import preferences as repo
from app.db.repositories import reference
from app.domain.geo import haversine_miles, nearest_zip
from app.domain.models import LatLng
from app.modules.preferences.schemas import (
    Coordinates,
    NotificationCategories,
    NotificationSettings,
    Place,
    Preferences,
    PreferencesIn,
    ZipInfo,
)

# "Use my location": search box around the device, widened once (FR-P3).
NEAREST_SPANS = ((0.75, 1.0), (1.5, 2.0))
NEAREST_MAX_MILES = 50.0
_TIMEZONES = frozenset(available_timezones())


def _not_set() -> ProblemError:
    return ProblemError(404, "preferences_not_set", "Finish onboarding first")


async def get_preferences(session: AsyncSession, user: User) -> Preferences:
    prefs = await repo.get(session, user.id)
    if prefs is None:
        raise _not_set()
    zip_row = await reference.get_zip(session, prefs.home_zip)
    return Preferences(
        favorite_team_ids=await repo.favorite_team_ids(session, user.id),
        home_zip=prefs.home_zip,
        home_place=Place(place_name=zip_row.place_name, state=zip_row.state) if zip_row else None,
        travel=prefs.travel,
        spending=prefs.spending,
        max_ticket_price_usd=(
            prefs.max_ticket_price_cents // 100 if prefs.max_ticket_price_cents else None
        ),
        viewing=prefs.viewing,
        notification_level=prefs.notification_level,
        timezone=user.timezone,
    )


async def save_preferences(session: AsyncSession, user: User, body: PreferencesIn) -> Preferences:
    team_ids = sorted(set(body.favorite_team_ids))
    unknown = set(team_ids) - await reference.existing_team_ids(session, team_ids)
    if unknown:
        raise ProblemError(422, "unknown_team", f"Unknown team: {', '.join(sorted(unknown))}")
    if await reference.get_zip(session, body.home_zip) is None:
        raise ProblemError(422, "zip_not_found", "We couldn't find that ZIP")
    if body.timezone not in _TIMEZONES:
        raise ProblemError(422, "invalid_timezone", "Unknown time zone")

    await repo.upsert(
        session,
        user.id,
        {
            "home_zip": body.home_zip,
            "travel": body.travel,
            "spending": body.spending,
            "max_ticket_price_cents": (
                body.max_ticket_price_usd * 100 if body.max_ticket_price_usd else None
            ),
            "viewing": body.viewing,
            "notification_level": body.notification_level,
        },
    )
    await repo.replace_favorites(session, user.id, team_ids)
    await repo.ensure_notification_settings(session, user.id)
    user.timezone = body.timezone
    await session.commit()
    return await get_preferences(session, user)


async def get_notification_settings(session: AsyncSession, user: User) -> NotificationSettings:
    prefs = await repo.get(session, user.id)
    if prefs is None:
        raise _not_set()
    categories = await repo.notification_settings(session, user.id)
    return NotificationSettings(
        level=prefs.notification_level,
        categories=NotificationCategories(
            **{c: categories.get(c, True) for c in NotificationCategories.model_fields}
        ),
    )


async def save_notification_settings(
    session: AsyncSession, user: User, body: NotificationSettings
) -> NotificationSettings:
    """Stores the user's choices; what each level allows is applied by the M5 alert policy."""
    if not await repo.exists(session, user.id):
        raise _not_set()
    await repo.set_notification_level(session, user.id, body.level)
    await repo.set_notification_settings(session, user.id, body.categories.model_dump())
    await session.commit()
    return await get_notification_settings(session, user)


async def lookup_zip(session: AsyncSession, zip_code: str) -> ZipInfo:
    row = await reference.get_zip(session, zip_code)
    if row is None:
        raise ProblemError(404, "zip_not_found", "We couldn't find that ZIP")
    return ZipInfo(zip=row.zip, place_name=row.place_name, state=row.state)


async def nearest(session: AsyncSession, where: Coordinates) -> ZipInfo:
    """Nearest ZIP to the device; the coordinates are neither stored nor logged (FR-P3a)."""
    point = LatLng(where.lat, where.lng)
    for lat_span, lng_span in NEAREST_SPANS:
        rows = await reference.zips_near(session, point.lat, point.lng, lat_span, lng_span)
        candidates = [(r, LatLng(r.lat, r.lng)) for r in rows]
        best = nearest_zip(point, candidates)
        if (
            best is not None
            and haversine_miles(point, LatLng(best.lat, best.lng)) <= NEAREST_MAX_MILES
        ):
            return ZipInfo(zip=best.zip, place_name=best.place_name, state=best.state)
    raise ProblemError(404, "zip_not_found", "No US ZIP near this location")
