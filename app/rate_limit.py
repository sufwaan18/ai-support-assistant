from collections import defaultdict, deque
from math import ceil
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status

from app.config import settings


class InMemoryRateLimiter:
    """Limit requests within one running application instance."""

    def __init__(
        self,
        *,
        limit: int,
        window_seconds: int,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def consume(
        self,
        identifier: str,
        *,
        now: float | None = None,
    ) -> int | None:
        """Record a request or return the retry delay when blocked."""
        current_time = monotonic() if now is None else now
        cutoff = current_time - self.window_seconds

        with self._lock:
            timestamps = self._requests[identifier]

            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= self.limit:
                retry_after = ceil(
                    self.window_seconds
                    - (current_time - timestamps[0])
                )
                return max(1, retry_after)

            timestamps.append(current_time)
            return None

    def clear(self) -> None:
        """Remove recorded requests, primarily for isolated tests."""
        with self._lock:
            self._requests.clear()


ai_rate_limiter = InMemoryRateLimiter(
    limit=settings.ai_rate_limit_requests,
    window_seconds=settings.ai_rate_limit_window_seconds,
)


def enforce_ai_rate_limit(request: Request) -> None:
    """Reject excessive AI requests from the same client address."""
    identifier = (
        request.client.host
        if request.client is not None
        else "unknown"
    )
    retry_after = ai_rate_limiter.consume(identifier)

    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many AI requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )