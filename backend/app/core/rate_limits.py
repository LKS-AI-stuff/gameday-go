"""API request limits per user and per IP (NFR-15, TDD §12).

slowapi's middleware runs before authentication and can't key by user, so the limits run as
router dependencies on slowapi's limiter (in-memory: one API instance in the MVP).
"""

import math
import time

from fastapi import Request
from limits import parse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.errors import ProblemError
from app.core.settings import Settings


class RateLimits:
    def __init__(self, settings: Settings) -> None:
        self._limiter = Limiter(key_func=get_remote_address)
        self._per_user = parse(f"{settings.rate_limit_per_min}/minute")
        self._per_ip = parse(f"{settings.rate_limit_ip_per_min}/minute")

    def _hit(self, item: object, key: str) -> None:
        strategy = self._limiter.limiter
        if not strategy.hit(item, key):  # type: ignore[arg-type]
            reset, _ = strategy.get_window_stats(item, key)  # type: ignore[arg-type]
            retry_after = max(1, math.ceil(reset - time.time()))
            raise ProblemError(
                429,
                "rate_limited",
                "Too many requests. Try again shortly.",
                headers={"Retry-After": str(retry_after)},
            )

    def check_user(self, user_id: str) -> None:
        self._hit(self._per_user, f"user:{user_id}")

    def check_ip(self, request: Request) -> None:
        self._hit(self._per_ip, f"ip:{get_remote_address(request)}")
