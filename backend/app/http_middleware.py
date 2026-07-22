import logging
from dataclasses import dataclass
from time import perf_counter

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings
from .services.rate_limit import api_rate_limiter


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitPolicy:
    scope: str
    limit: int


def client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")

    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()

    if request.client is not None:
        return request.client.host

    return "unknown"


def rate_limit_policy(path: str) -> RateLimitPolicy | None:
    if path == "/api/search":
        return RateLimitPolicy(
            scope="search",
            limit=settings.public_api_search_max_requests_per_window,
        )

    if path == "/api/movies" or path.startswith("/api/movies/"):
        return RateLimitPolicy(
            scope="catalog",
            limit=settings.public_api_catalog_max_requests_per_window,
        )

    return None


def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )
    return response


class ProductionHttpMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started_at = perf_counter()
        policy = (
            rate_limit_policy(request.url.path)
            if settings.public_api_rate_limit_enabled
            else None
        )
        decision = None

        if policy is not None:
            decision = api_rate_limiter.check(
                scope=policy.scope,
                client_id=client_identifier(request),
                limit=policy.limit,
                window_seconds=settings.public_api_rate_limit_window_seconds,
            )

            if not decision.allowed:
                response = JSONResponse(
                    status_code=429,
                    content={
                        "detail": "request limit exceeded; try again shortly",
                    },
                )
                response.headers["Retry-After"] = str(
                    decision.retry_after_seconds
                )
                response.headers["X-RateLimit-Limit"] = str(decision.limit)
                response.headers["X-RateLimit-Remaining"] = "0"
                logger.warning(
                    "http rate limit path=%s client=%s",
                    request.url.path,
                    client_identifier(request),
                )
                return add_security_headers(response)

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "http request failed method=%s path=%s latency_ms=%.1f",
                request.method,
                request.url.path,
                (perf_counter() - started_at) * 1000,
            )
            raise

        if decision is not None:
            response.headers["X-RateLimit-Limit"] = str(decision.limit)
            response.headers["X-RateLimit-Remaining"] = str(
                decision.remaining
            )

        logger.info(
            "http request method=%s path=%s status=%s latency_ms=%.1f",
            request.method,
            request.url.path,
            response.status_code,
            (perf_counter() - started_at) * 1000,
        )

        return add_security_headers(response)