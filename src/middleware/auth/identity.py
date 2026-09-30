"""Read identity only from FastMCP's verified access-token context."""

import json
from uuid import UUID

from fastmcp.server.auth import AccessToken
from fastmcp.server.dependencies import get_access_token


def user_id(token: AccessToken) -> str:
    subject = token.claims.get("sub")
    if not isinstance(subject, str):
        raise ValueError("An authenticated Supabase user is required.")
    return str(UUID(subject))


def require_user_token() -> AccessToken:
    token = get_access_token()
    if token is None:
        raise ValueError("An authenticated Supabase user is required.")
    user_id(token)
    return token


def rate_limit_identity(token: AccessToken) -> str:
    return json.dumps([token.claims["iss"], user_id(token)], separators=(",", ":"))
