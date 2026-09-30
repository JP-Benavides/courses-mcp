"""Validated configuration for the Supabase OAuth resource server."""

from dataclasses import dataclass
import os
from urllib.parse import urlsplit


def https_origin(name: str) -> str:
    value = os.environ.get(name, "").strip().rstrip("/")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment or parsed.path):
        raise ValueError(f"{name} must be an HTTPS origin without a path or credentials.")
    return value


@dataclass(frozen=True)
class OAuthConfig:
    project_url: str
    public_url: str
    algorithm: str

    @property
    def issuer(self) -> str:
        return f"{self.project_url}/auth/v1"

    @property
    def resource(self) -> str:
        return f"{self.public_url}/mcp"

    @classmethod
    def from_env(cls):
        project = https_origin("SUPABASE_URL")
        public = https_origin("MCP_PUBLIC_URL")
        algorithm = os.environ.get("MCP_JWT_ALGORITHM", "ES256").strip()
        if algorithm not in {"ES256", "RS256"}:
            raise ValueError("MCP_JWT_ALGORITHM must be ES256 or RS256.")
        return cls(project, public, algorithm)
