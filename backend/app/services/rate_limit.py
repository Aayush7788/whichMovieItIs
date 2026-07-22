from dataclasses import dataclass
from math import ceil
from threading import Lock
from time import monotonic


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._lock = Lock()
        self._request_times: dict[tuple[str, str], list[float]] = {}

    def check(
        self,
        scope: str,
        client_id: str,
        limit: int,
        window_seconds: int,
        now: float | None = None,
    ) -> RateLimitDecision:
        checked_at = monotonic() if now is None else now
        cutoff = checked_at - window_seconds
        key = (scope, client_id)

        with self._lock:
            request_times = [
                request_time
                for request_time in self._request_times.get(key, [])
                if request_time > cutoff
            ]

            if len(request_times) >= limit:
                retry_after_seconds = max(
                    1,
                    ceil(window_seconds - (checked_at - request_times[0])),
                )
                self._request_times[key] = request_times
                return RateLimitDecision(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    retry_after_seconds=retry_after_seconds,
                )

            request_times.append(checked_at)
            self._request_times[key] = request_times

        return RateLimitDecision(
            allowed=True,
            limit=limit,
            remaining=max(0, limit - len(request_times)),
            retry_after_seconds=0,
        )

    def clear(self) -> None:
        with self._lock:
            self._request_times.clear()


api_rate_limiter = SlidingWindowRateLimiter()