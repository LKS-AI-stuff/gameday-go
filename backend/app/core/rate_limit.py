"""In-process async token bucket for outbound provider calls (TDD §8.2 step 3)."""

import asyncio
import time
from collections.abc import Awaitable, Callable


class RateLimiter:
    """Allows `per_minute` calls per minute with bursts up to that size; callers wait, not fail."""

    def __init__(
        self,
        per_minute: int,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if per_minute <= 0:
            raise ValueError("per_minute must be positive")
        self._capacity = float(per_minute)
        self._rate = per_minute / 60.0
        self._tokens = self._capacity
        self._clock = clock
        self._sleep = sleep
        self._updated = clock()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = self._clock()
        self._tokens = min(self._capacity, self._tokens + (now - self._updated) * self._rate)
        self._updated = now

    async def acquire(self) -> None:
        async with self._lock:
            self._refill()
            while self._tokens < 1:
                await self._sleep((1 - self._tokens) / self._rate)
                self._refill()
            self._tokens -= 1
