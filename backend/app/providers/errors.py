"""Provider errors shared by adapters. Messages never carry URLs, keys or response bodies."""

from app.core.settings import Provider


class ProviderError(Exception):
    def __init__(self, provider: Provider, endpoint: str, status: int | None = None) -> None:
        super().__init__(f"{provider} {endpoint} failed" + (f" ({status})" if status else ""))
        self.provider = provider
        self.endpoint = endpoint
        self.status = status
