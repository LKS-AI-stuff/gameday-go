from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.core.errors import ProblemError
from app.core.logging import get_logger
from app.db.session import get_engine

router = APIRouter(tags=["ops"])
log = get_logger(__name__)


class Health(BaseModel):
    status: Literal["ok"] = "ok"


@router.get("/health", operation_id="getHealth")
async def health() -> Health:
    """Liveness: the process is up."""
    return Health()


@router.get("/ready", operation_id="getReady")
async def ready() -> Health:
    """Readiness: the database answers."""
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("select 1"))
    except Exception as exc:
        log.warning("db_not_ready", error_type=type(exc).__name__)
        raise ProblemError(503, "db_unavailable", "Database unavailable") from exc
    return Health()
