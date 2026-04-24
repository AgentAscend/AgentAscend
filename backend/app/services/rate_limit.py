from __future__ import annotations

import time
from collections import defaultdict, deque

from backend.app.services.error_response import fail

_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def enforce_rate_limit(scope: str, key: str, limit: int, window_seconds: int) -> None:
    now = time.time()
    bucket_key = f"{scope}:{key or 'anonymous'}"
    q = _BUCKETS[bucket_key]

    cutoff = now - window_seconds
    while q and q[0] < cutoff:
        q.popleft()

    if len(q) >= limit:
        fail(429, "rate_limited", f"Rate limit exceeded for {scope}")

    q.append(now)
