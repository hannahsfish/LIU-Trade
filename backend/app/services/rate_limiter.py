import asyncio
import time
from collections import deque


class RateLimiter:
    """Token bucket rate limiter for Alpha Vantage API (75 calls/min)."""

    def __init__(self, max_calls: int = 75, period_seconds: float = 60.0):
        self._max_calls = max_calls
        self._period = period_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()
        self.total_calls = 0
        self.waits = 0

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            while self._timestamps and self._timestamps[0] <= now - self._period:
                self._timestamps.popleft()

            if len(self._timestamps) >= self._max_calls:
                sleep_until = self._timestamps[0] + self._period
                wait_time = sleep_until - now
                if wait_time > 0:
                    self.waits += 1
                    await asyncio.sleep(wait_time)
                    now = time.monotonic()
                    while self._timestamps and self._timestamps[0] <= now - self._period:
                        self._timestamps.popleft()

            self._timestamps.append(now)
            self.total_calls += 1

    @property
    def remaining(self) -> int:
        now = time.monotonic()
        active = sum(1 for t in self._timestamps if t > now - self._period)
        return max(0, self._max_calls - active)

    def stats(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "remaining_this_minute": self.remaining,
            "total_waits": self.waits,
        }


av_limiter = RateLimiter(max_calls=72, period_seconds=60.0)
