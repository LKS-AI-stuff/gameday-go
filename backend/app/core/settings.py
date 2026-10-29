"""Application settings, loaded from environment variables (TDD §13).

Locally they come from the git-ignored `.env` at the repository root.
Settings are added milestone by milestone, as the features that use them land.
"""

from datetime import time
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]

type Provider = Literal["apisports", "ticketmaster", "places", "openai", "resend"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["local", "ci", "production"] = "local"
    log_level: str = "INFO"
    public_web_url: str = "http://localhost:8081"
    # Comma-separated list of allowed browser origins (Expo web dev server locally).
    cors_origins: str = "http://localhost:8081"

    # Backend role `gamedaygo_app`, which owns schema `app` (TDD §6.1).
    database_url: SecretStr
    # Admin connection, used only by `cli bootstrap-db` to create the role and schema.
    database_admin_url: SecretStr | None = None

    supabase_url: str = "http://127.0.0.1:54321"
    supabase_jwt_mode: Literal["jwks", "secret"] = "jwks"
    supabase_jwt_secret: SecretStr | None = None
    supabase_jwt_audience: str = "authenticated"
    # Server-only Supabase secret key: Auth Admin API for account deletion (FR-A4, TDD §6).
    supabase_secret_key: SecretStr | None = None

    # Kill switches (FR-O5). Keys and budgets are added with each provider's milestone.
    provider_apisports_enabled: bool = True
    provider_ticketmaster_enabled: bool = True
    provider_places_enabled: bool = True
    provider_openai_enabled: bool = True
    provider_resend_enabled: bool = True

    # API-Sports (TDD §8.3, §13). Pro plan: 7,500 requests/day; the budget is a safety cap.
    apisports_key: SecretStr | None = None
    apisports_base_url: str = "https://v1.american-football.api-sports.io"
    apisports_league_id: int = 1
    apisports_daily_budget: int = 1000
    apisports_reserve_pct: int = 10
    apisports_rate_per_min: int = 10
    provider_budget_warn_pct: int = 80

    # Product rules (TDD §13).
    planning_window_days: int = 30
    # Until the Super Bowl is listed, a season ends this long after its last known game (BR-W2).
    season_end_fallback_days: int = 30
    local_area_miles: float = 75.0
    primetime_start_et: time = time(19, 0)

    # API rate limits (NFR-15).
    rate_limit_per_min: int = 60
    rate_limit_ip_per_min: int = 60

    @model_validator(mode="after")
    def _check_jwt_mode(self) -> "Settings":
        if self.supabase_jwt_mode == "secret" and self.supabase_jwt_secret is None:
            raise ValueError("SUPABASE_JWT_SECRET is required when SUPABASE_JWT_MODE=secret")
        return self

    @model_validator(mode="after")
    def _check_provider_keys(self) -> "Settings":
        # An enabled provider must have its key (TDD §13); CI turns API-Sports off.
        if self.provider_apisports_enabled and self.apisports_key is None:
            raise ValueError("APISPORTS_KEY is required when PROVIDER_APISPORTS_ENABLED=true")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def jwt_issuer(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @property
    def jwks_url(self) -> str:
        return f"{self.jwt_issuer}/.well-known/jwks.json"

    def provider_enabled(self, provider: Provider) -> bool:
        enabled: bool = getattr(self, f"provider_{provider}_enabled")
        return enabled


@lru_cache
def get_settings() -> Settings:
    return Settings()  # required values come from the environment
