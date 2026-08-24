"""Small in-process rate limiters for the demo deployment.

These intentionally use only the standard library. For a multi-instance
production deployment, replace the stores with Redis or another shared store.
"""

from collections import defaultdict, deque
from threading import Lock
from time import monotonic


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = max(1, limit)
        self.window_seconds = max(1, window_seconds)
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True


class LoginFailureLimiter:
    def __init__(self, limit: int = 5, window_seconds: int = 900) -> None:
        self.limit = max(1, limit)
        self.window_seconds = max(1, window_seconds)
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def blocked(self, key: str) -> bool:
        now = monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            failures = self._failures[key]
            while failures and failures[0] <= cutoff:
                failures.popleft()
            return len(failures) >= self.limit

    def record_failure(self, key: str) -> None:
        now = monotonic()
        with self._lock:
            self._failures[key].append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
