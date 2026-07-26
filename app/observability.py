"""Small, dependency-free operational safeguards for the modular monolith.

The in-memory limiter is intentionally a P0 safety net.  The public interface
is kept independent from storage so P1 can replace it with Redis without
changing endpoint code.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import HTTPException, Request, status

logger = logging.getLogger("zhiday.operations")


def privacy_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def client_fingerprint(request: Request, subject: str = "") -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    address = forwarded.split(",", 1)[0].strip() or (request.client.host if request.client else "unknown")
    return f"{privacy_hash(address)}:{privacy_hash(subject.strip().lower()) if subject else '-'}"


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, *, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        with self._lock:
            events = self._events[key]
            threshold = now - window_seconds
            while events and events[0] <= threshold:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(window_seconds - (now - events[0])))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="操作过于频繁，请稍后再试",
                    headers={"Retry-After": str(retry_after)},
                )
            events.append(now)


rate_limiter = SlidingWindowRateLimiter()


def enforce_rate_limit(request: Request, scope: str, subject: str, *, limit: int, window_seconds: int) -> None:
    rate_limiter.check(
        f"{scope}:{client_fingerprint(request, subject)}",
        limit=max(1, limit),
        window_seconds=max(1, window_seconds),
    )


def log_event(name: str, **fields: object) -> None:
    safe = " ".join(f"{key}={value}" for key, value in fields.items() if value not in (None, ""))
    logger.info("event=%s %s", name, safe)
