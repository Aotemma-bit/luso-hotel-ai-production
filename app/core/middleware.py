import asyncio
import hashlib
import logging
import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
try:
    from redis.asyncio import Redis
except ImportError:  # Allows unit tests before optional infrastructure is installed.
    Redis = None

from app.core.config import settings


logger = logging.getLogger("luso.requests")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("unhandled_request_error", extra={"request_id": request_id, "method": request.method, "path": request.url.path})
            raise
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self' https://*.supabase.co wss://*.supabase.co; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        logger.info("request_completed", extra={"request_id": request_id, "method": request.method, "path": request.url.path, "status_code": response.status_code, "duration_ms": round((time.perf_counter() - started) * 1000, 2)})
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()
        self._redis = Redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url and Redis else None

    @staticmethod
    def _identity(request: Request) -> str:
        authorization = request.headers.get("authorization", "")
        if authorization:
            return hashlib.sha256(authorization.encode()).hexdigest()[:24]
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        return forwarded or (request.client.host if request.client else "unknown")

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/") or request.url.path in {"/api/health", "/api/health/live"}:
            return await call_next(request)
        key = self._identity(request)
        if self._redis is not None:
            bucket = int(time.time()) // settings.rate_limit_window_seconds
            redis_key = f"luso:rate:{bucket}:{key}"
            try:
                count = await self._redis.incr(redis_key)
                if count == 1:
                    await self._redis.expire(redis_key, settings.rate_limit_window_seconds + 2)
                if count > settings.rate_limit_requests:
                    return JSONResponse(status_code=429, content={"detail": "Too many requests. Please try again shortly."}, headers={"Retry-After": str(settings.rate_limit_window_seconds)})
                return await call_next(request)
            except Exception:
                logger.exception("redis_rate_limit_unavailable")
        now = time.monotonic()
        cutoff = now - settings.rate_limit_window_seconds
        async with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= settings.rate_limit_requests:
                return JSONResponse(status_code=429, content={"detail": "Too many requests. Please try again shortly."}, headers={"Retry-After": str(settings.rate_limit_window_seconds)})
            events.append(now)
        return await call_next(request)
