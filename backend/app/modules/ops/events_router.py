from datetime import UTC, datetime

from fastapi import APIRouter, Response

from app.modules.identity.dependencies import ConfirmedUser, Session
from app.modules.ops import events

router = APIRouter(tags=["ops"])


@router.post("/app-events", operation_id="postAppEvents", status_code=202, response_class=Response)
async def post_app_events(
    batch: events.EventBatch, user: ConfirmedUser, session: Session
) -> Response:
    """Up to 20 allowlisted product events (TDD §15.1)."""
    await events.record(session, user, batch, datetime.now(UTC))
    return Response(status_code=202)
