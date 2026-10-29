"""Schedule sync: upsert, change detection, unmapped records, failures, rollover
(FR-O1, FR-O2, FR-LS10, FR-O5, BR-W2, AC-49)."""

import copy
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import asyncpg
import httpx
import pytest
import respx
from sqlalchemy import text

from app.core.budgets import BudgetStore
from app.core.http import ProviderClient
from app.db.session import get_engine, get_sessionmaker
from app.modules.schedule import service as schedule_service
from app.modules.schedule.sync import schedule_sync
from app.providers.apisports.live import ApiSportsProvider
from app.providers.apisports.mock import FixtureScheduleProvider, load_fixture
from tests.conftest import make_settings
from tests.integration.conftest import NOW, SEASON, reset_season

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("season_data")]


@pytest.fixture
async def restore_season() -> AsyncIterator[None]:
    """Tests here change the schedule; put the recorded season back afterwards."""
    yield
    await reset_season()


def recorded() -> dict[str, Any]:
    return copy.deepcopy(load_fixture("games_2026"))


def first_upcoming(payload: dict[str, Any]) -> dict[str, Any]:
    item: dict[str, Any] = next(
        i
        for i in payload["response"]
        if i["game"]["stage"] == "Regular Season"
        and i["game"]["status"]["short"] == "NS"
        and i["game"]["date"]["time"] != "00:00"
    )
    return item


async def sync(payload: dict[str, Any], now: datetime = NOW, **games: dict[str, Any]) -> Any:
    provider = FixtureScheduleProvider(
        {SEASON: payload, **{int(k): v for k, v in games.items()}}, now=now
    )
    return await schedule_sync(get_sessionmaker(), provider, make_settings(), now=now)


async def test_resync_is_idempotent(app_conn: asyncpg.Connection, restore_season: None) -> None:
    before = await app_conn.fetchval("select count(*) from app.games")
    result = await sync(recorded())
    assert result.status == "succeeded" and result.changes == 0
    assert await app_conn.fetchval("select count(*) from app.games") == before == result.records
    run = await app_conn.fetchrow("select * from app.sync_runs where id = $1", result.run_id)
    assert run["status"] == "succeeded" and run["season"] == SEASON and run["ended_at"]


async def test_moved_kickoff_is_recorded_once(
    app_conn: asyncpg.Connection, restore_season: None
) -> None:
    payload = recorded()
    item = first_upcoming(payload)
    item["game"]["date"]["timestamp"] += 3 * 3600
    item["game"]["date"]["time"] = "21:25"

    result = await sync(payload)

    assert result.changes == 1
    change = await app_conn.fetchrow(
        "select c.field, c.old_value, c.new_value, g.apisports_game_id from app.game_changes c "
        "join app.games g on g.id = c.game_id where c.sync_run_id = $1",
        result.run_id,
    )
    assert change["field"] == "kickoff_at"
    assert change["apisports_game_id"] == str(item["game"]["id"])
    assert change["old_value"] != change["new_value"]
    again = await sync(payload)
    assert again.changes == 0


async def test_unmapped_team_is_skipped_not_misattached(
    app_conn: asyncpg.Connection, restore_season: None
) -> None:
    """FR-LS10, AC-36: a record that can't be mapped is never attached to a game."""
    payload = recorded()
    item = first_upcoming(payload)
    item["teams"]["home"]["id"] = 4242
    game_id = str(item["game"]["id"])
    await app_conn.execute("delete from app.games where apisports_game_id = $1", game_id)

    result = await sync(payload)

    assert result.status == "succeeded"
    assert (
        await app_conn.fetchval(
            "select count(*) from app.games where apisports_game_id = $1", game_id
        )
        == 0
    )


async def test_kill_switch_fails_the_run_and_keeps_games(app_conn: asyncpg.Connection) -> None:
    settings = make_settings(provider_apisports_enabled=False, apisports_key=None)
    before = await app_conn.fetchval("select max(last_synced_at) from app.games")
    with respx.mock(assert_all_called=False) as router:
        route = router.get(url__regex=r".*api-sports.*")
        client = ProviderClient(settings)
        result = await schedule_sync(
            get_sessionmaker(), ApiSportsProvider(client, settings), settings, now=NOW
        )
        await client.aclose()
    assert not route.called
    assert result.status == "failed" and result.error == "ProviderDisabled"
    assert await app_conn.fetchval("select max(last_synced_at) from app.games") == before
    run = await app_conn.fetchrow(
        "select status, error from app.sync_runs where id = $1", result.run_id
    )
    assert dict(run) == {"status": "failed", "error": "ProviderDisabled"}


async def test_budget_exhausted_sends_nothing(app_conn: asyncpg.Connection) -> None:
    # A budget fully held in reserve: nothing is available for a schedule sync.
    settings = make_settings(apisports_daily_budget=1, apisports_reserve_pct=100)
    await app_conn.execute("delete from app.provider_budgets")
    with respx.mock(assert_all_called=False) as router:
        route = router.get(url__regex=r".*api-sports.*").mock(return_value=httpx.Response(200))
        client = ProviderClient(settings, budgets=BudgetStore(get_engine(), settings))
        result = await schedule_sync(
            get_sessionmaker(), ApiSportsProvider(client, settings), settings, now=NOW
        )
        await client.aclose()
    assert not route.called
    assert result.error == "BudgetExhausted"
    await app_conn.execute("delete from app.provider_budgets")


async def test_rollover_after_super_bowl_shows_next_season_not_released(
    app_conn: asyncpg.Connection, restore_season: None
) -> None:
    """BR-W2, AC-49."""
    # The recorded feed lists the Super Bowl as "Pro Bowl"; here it has been played.
    payload = recorded()
    super_bowl = next(i for i in payload["response"] if i["game"]["week"] == "Pro Bowl")
    super_bowl["game"]["status"] = {"short": "FT", "long": "Finished", "timer": None}
    after = datetime(2027, 2, 16, tzinfo=UTC)
    async with get_sessionmaker()() as session:
        await session.execute(text("DELETE FROM app.seasons"))
        await session.commit()

    result = await sync(payload, now=after, **{"2027": {"response": []}})

    assert result.status == "succeeded" and result.seasons == (2026, 2027)
    seasons = {r["year"]: r["status"] for r in await app_conn.fetch("select * from app.seasons")}
    assert seasons == {2026: "completed", 2027: "upcoming"}
    async with get_sessionmaker()() as session:
        season = await schedule_service.get_season(session, make_settings(), after)
    assert season.year == 2027
    assert season.schedule_available is False
    assert season.weeks == [] and season.current_week is None


async def test_season_doesnt_end_after_the_conference_championships(
    app_conn: asyncpg.Connection, restore_season: None
) -> None:
    """With the Super Bowl not listed yet, early February is still the 2026 season (BR-W2)."""
    payload = recorded()
    payload["response"] = [i for i in payload["response"] if i["game"]["week"] != "Pro Bowl"]
    feb_5 = datetime(2027, 2, 5, tzinfo=UTC)
    async with get_sessionmaker()() as session:
        await session.execute(text("DELETE FROM app.seasons"))
        await session.commit()

    result = await sync(payload, now=feb_5, **{"2027": {"response": []}})

    assert result.seasons == (2026,)
    async with get_sessionmaker()() as session:
        season = await schedule_service.get_season(session, make_settings(), feb_5)
    assert season.year == 2026 and season.schedule_available is True


async def test_super_bowl_is_stored_as_week_22(app_conn: asyncpg.Connection) -> None:
    row = await app_conn.fetchrow(
        "select g.week, g.venue_name, s.super_bowl_game_id = g.id as linked "
        "from app.games g join app.seasons s on s.year = g.season where g.week = 22"
    )
    assert row is not None
    assert (row["week"], row["venue_name"], row["linked"]) == (22, "SoFi Stadium", True)
