"""Builds live providers (TDD §8.1). Tests construct fixture providers directly."""

from app.core.budgets import BudgetStore
from app.core.http import ProviderClient
from app.core.settings import Settings
from app.db.session import get_engine
from app.providers.apisports.base import ScheduleProvider
from app.providers.apisports.live import ApiSportsProvider


def provider_client(settings: Settings) -> ProviderClient:
    return ProviderClient(settings, budgets=BudgetStore(get_engine(), settings))


def schedule_provider(settings: Settings, client: ProviderClient) -> ScheduleProvider:
    return ApiSportsProvider(client, settings)
