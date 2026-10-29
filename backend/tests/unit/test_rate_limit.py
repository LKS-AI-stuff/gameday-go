"""Outbound token bucket (TDD §8.2 step 3)."""

import pytest

from app.core.rate_limit import RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


async def test_burst_up_to_the_limit_then_waits() -> None:
    clock = FakeClock()
    limiter = RateLimiter(10, clock=clock, sleep=clock.sleep)
    for _ in range(10):
        await limiter.acquire()
    assert clock.slept == []
    await limiter.acquire()  # the 11th call within a minute waits for one token (6 s)
    assert clock.slept == [pytest.approx(6.0)]


async def test_tokens_refill_over_time() -> None:
    clock = FakeClock()
    limiter = RateLimiter(10, clock=clock, sleep=clock.sleep)
    for _ in range(10):
        await limiter.acquire()
    clock.now += 60
    for _ in range(10):
        await limiter.acquire()
    assert clock.slept == []


def test_rejects_non_positive_rate() -> None:
    with pytest.raises(ValueError):
        RateLimiter(0)
