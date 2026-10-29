import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.modules.identity.dependencies import AppSettings, ConfirmedUser, Session
from app.modules.schedule import schemas, service

router = APIRouter(tags=["schedule"])


@router.get("/teams", operation_id="listTeams")
async def list_teams(user: ConfirmedUser, session: Session) -> list[schemas.Team]:
    del user
    return await service.list_teams(session)


@router.get("/season", operation_id="getSeason")
async def get_season(
    user: ConfirmedUser, session: Session, settings: AppSettings
) -> schemas.Season:
    """Active season, whether its schedule is out, weeks and freshness (FR-O1c, FR-SC4)."""
    del user
    return await service.get_season(session, settings, service.utcnow())


@router.get("/games", operation_id="listGames")
async def list_games(
    user: ConfirmedUser,
    session: Session,
    settings: AppSettings,
    season: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    week: Annotated[int | None, Query(ge=1, le=22)] = None,
    team: Annotated[str | None, Query(min_length=1, max_length=8)] = None,
    favorites: bool = False,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: datetime | None = None,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=service.MAX_PAGE)] = 50,
) -> schemas.GamePage:
    """Season games by week, team or the caller's favorites; cursor-paginated (FR-SC1, FR-SC2)."""
    return await service.list_games(
        session,
        settings,
        user,
        service.utcnow(),
        season=season,
        week=week,
        team=team,
        favorites=favorites,
        from_=from_,
        to=to,
        cursor=cursor,
        limit=limit,
    )


@router.get("/games/{game_id}", operation_id="getGame")
async def get_game(
    game_id: uuid.UUID, user: ConfirmedUser, session: Session, settings: AppSettings
) -> schemas.GameDetail:
    return await service.get_game(session, settings, user, game_id, service.utcnow())
