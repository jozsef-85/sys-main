from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from typing import Callable

from fastapi import HTTPException, Request, status


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("cf-connecting-ip") or request.headers.get("x-real-ip")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class MemoryRateLimiter:
    def __init__(
        self,
        limit: int,
        window_seconds: int,
        key_builder: Callable[[Request], str],
        detail: str,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.key_builder = key_builder
        self.detail = detail
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def __call__(self, request: Request) -> None:
        key = self.key_builder(request)
        now = monotonic()
        boundary = now - self.window_seconds

        with self._lock:
            events = self._events[key]
            while events and events[0] <= boundary:
                events.popleft()

            if len(events) >= self.limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=self.detail,
                    headers={"Retry-After": str(self.window_seconds)},
                )

            events.append(now)
