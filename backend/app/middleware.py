"""Lightweight in-memory per-IP rate limiting.

Good enough for a single-process demo/dev deployment. For production behind
multiple workers, enforce limits at the gateway or with a shared store (Redis).
Streaming (SSE) and health endpoints are exempt so long-lived connections and
liveness probes are not throttled.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings

_EXEMPT_SUFFIXES = ("/health", "/stream", "/docs", "/openapi.json")


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self._hits: dict[str, deque] = defaultdict(deque)
        self._limit = max(1, settings.rate_limit_per_minute)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method == "OPTIONS" or any(path.endswith(s) for s in _EXEMPT_SUFFIXES):
            return await call_next(request)

        client = request.client.host if request.client else "anonymous"
        now = time.monotonic()
        window = self._hits[client]
        # evict entries older than 60s
        while window and now - window[0] > 60.0:
            window.popleft()

        if len(window) >= self._limit:
            retry = max(1, int(60 - (now - window[0])))
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please slow down."},
                headers={"Retry-After": str(retry)},
            )

        window.append(now)
        return await call_next(request)
