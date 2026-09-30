import math
import os

from fastmcp.server.dependencies import get_access_token
from src.middleware.auth.identity import rate_limit_identity
from fastmcp.server.middleware import MiddlewareContext
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware


def _client_id(context: MiddlewareContext) -> str:
    # OAuth client_id identifies ChatGPT, not the individual user.
    token = get_access_token()
    return rate_limit_identity(token) if token is not None else "local:shared"


def create_rate_limiter() -> RateLimitingMiddleware:
    """
    Allow a burst of 15 requests, replenishing five requests per second by default.
    The caller loads .env before invoking this factory. Invalid settings stop
    startup rather than silently disabling protection.
    """
    try:
        rate = float(os.environ.get("MCP_RATE_LIMIT_PER_SECOND", "5"))
        burst = int(os.environ.get("MCP_RATE_LIMIT_BURST", "15"))
    except ValueError as error:
        raise ValueError("Rate limit settings must be numeric; burst must be an integer.") from error
    if not math.isfinite(rate) or rate <= 0 or burst <= 0:
        raise ValueError("MCP_RATE_LIMIT_PER_SECOND and MCP_RATE_LIMIT_BURST must be positive and finite.")
    return RateLimitingMiddleware(
        max_requests_per_second=rate,
        burst_capacity=burst,
        get_client_id=_client_id,
    )
