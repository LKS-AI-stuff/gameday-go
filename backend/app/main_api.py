"""FastAPI app factory (API entry point).

Run locally: uv run uvicorn app.main_api:create_app --factory --reload
"""

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import APIRouter, Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.core.auth import TokenVerifier
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging, get_logger
from app.core.rate_limits import RateLimits
from app.core.settings import Settings, get_settings
from app.core.supabase_admin import SupabaseAdmin
from app.db.session import get_engine
from app.modules.identity.dependencies import ip_rate_limit, user_rate_limit
from app.modules.identity.router import router as identity_router
from app.modules.ops.events_router import router as events_router
from app.modules.ops.router import router as ops_router
from app.modules.preferences.router import router as preferences_router
from app.modules.schedule.router import router as schedule_router

API_PREFIX = "/api/v1"

log = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.token_verifier = TokenVerifier(settings)
        app.state.supabase_admin = SupabaseAdmin(settings)
        log.info("api_started", app_env=settings.app_env, jwt_mode=settings.supabase_jwt_mode)
        yield
        await app.state.token_verifier.aclose()
        await app.state.supabase_admin.aclose()
        await get_engine().dispose()

    app = FastAPI(
        title="GameDay Go API",
        version="0.1.0",
        lifespan=lifespan,
        # Interactive docs are off in production (TDD §13 production guards).
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else f"{API_PREFIX}/openapi.json",
    )
    app.state.settings = settings
    app.state.rate_limits = RateLimits(settings)
    install_error_handlers(app)

    @app.middleware("http")
    async def request_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=rid)
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    # Locally the Expo web dev server is a different origin. In M6 the web app is
    # served by this API (same origin), so CORS stays closed (TDD §14).
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
            expose_headers=["X-Request-ID"],
        )

    api = APIRouter(prefix=API_PREFIX)
    api.include_router(ops_router, dependencies=[Depends(ip_rate_limit)])
    # Every authenticated route counts against the caller's per-user limit (NFR-15).
    for router in (identity_router, preferences_router, schedule_router, events_router):
        api.include_router(router, dependencies=[Depends(user_rate_limit)])
    app.include_router(api)
    return app
