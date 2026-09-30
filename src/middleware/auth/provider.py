"""Supabase issues OAuth tokens; this server validates its own resource audience."""

import math
import time

from fastmcp.server.auth import RemoteAuthProvider
from fastmcp.server.auth.providers.jwt import JWTVerifier
from pydantic import AnyHttpUrl

from src.middleware.auth.config import OAuthConfig
from src.middleware.auth.identity import user_id

# Supabase OIDC scopes do not grant database permissions. RLS handles data access.
OAUTH_SCOPES = ["openid", "offline_access"]
TOOL_AUTH_META = {"securitySchemes": [{"type": "oauth2", "scopes": OAUTH_SCOPES}]}


class SupabaseUserVerifier(JWTVerifier):
    async def verify_token(self, token: str):
        try:
            verified = await super().verify_token(token)
        except OverflowError:
            return None
        if verified is None:
            return None
        claims = verified.claims
        try:
            user_id(verified)
            exp = claims.get("exp")
            nbf = claims.get("nbf", 0)
            for value in (exp, nbf):
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    return None
            if exp <= time.time() or nbf > time.time():
                return None
            client_id = claims.get("client_id")
            if (claims.get("role") != "authenticated"
                    or claims.get("is_anonymous") is not False
                    or not isinstance(client_id, str)
                    or not client_id.strip()
                    or client_id != client_id.strip()
                    or not client_id.isprintable()):
                return None
        except (ValueError, TypeError, AttributeError, OverflowError):
            return None
        return verified


def create_auth(config: OAuthConfig) -> RemoteAuthProvider:
    verifier = SupabaseUserVerifier(
        jwks_uri=f"{config.issuer}/.well-known/jwks.json",
        issuer=config.issuer,
        audience=config.resource,
        algorithm=config.algorithm,
    )
    return RemoteAuthProvider(
        token_verifier=verifier,
        authorization_servers=[AnyHttpUrl(config.issuer)],
        base_url=config.public_url,
        scopes_supported=OAUTH_SCOPES,
        challenge_scopes=OAUTH_SCOPES,
        resource_name="Courses MCP",
    )
