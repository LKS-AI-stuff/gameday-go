"""Client product events (TDD §15.1): allowlisted names only, no free text (SM1, SM4)."""

from datetime import datetime, timedelta
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ProblemError
from app.db.models import AppEvent, User

EventName = Literal[
    "onboarding_started",
    "onboarding_completed",
    "plan_requested",
    "plan_first_step_rendered",
    "plan_card_rendered",
    "plan_saved",
    "watch_created",
]
MAX_CLOCK_SKEW = timedelta(days=1)


class EmptyProps(BaseModel):
    """No properties yet; anything sent is rejected rather than stored."""

    model_config = ConfigDict(extra="forbid")


class ClientEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: EventName
    platform: Literal["ios", "android", "web"]
    client_ts: datetime
    props: EmptyProps = Field(default_factory=EmptyProps)


class EventBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: Annotated[list[ClientEvent], Field(min_length=1, max_length=20)]


async def record(session: AsyncSession, user: User, batch: EventBatch, now: datetime) -> None:
    for event in batch.events:
        if event.client_ts.tzinfo is None or abs(event.client_ts - now) > MAX_CLOCK_SKEW:
            raise ProblemError(422, "invalid_client_ts", "client_ts must be a recent UTC time")
    for event in batch.events:
        session.add(
            AppEvent(
                user_id=user.id,
                name=event.name,
                platform=event.platform,
                client_ts=event.client_ts,
                props={},
            )
        )
    await session.commit()
