import math
import os

from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import MiddlewareContext
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware


def _client_id(context: MiddlewareContext) -> str:
    # Use the verified identity, not the raw token or a caller-supplied header.
    # New tokens and sessions for the same developer share the same allowance.
    token = get_access_token()
    return f"developer:{token.client_id}" if token is not None else "local:shared"


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
