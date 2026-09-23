"""Issue a locally signed JWT for a developer; only the issuer needs the private key."""

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import jwt
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.providers import FileSystemProvider

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ISSUER = "courses-mcp-local"
DEFAULT_AUDIENCE = "courses-mcp"


def create_server() -> FastMCP:
    project_root = PROJECT_ROOT
    load_dotenv(project_root / ".env")
    public_key_path = Path(os.environ.get("MCP_JWT_PUBLIC_KEY_FILE", ".auth/public.pem"))
    if not public_key_path.is_absolute():
        public_key_path = project_root / public_key_path
    issuer = os.environ.get("MCP_JWT_ISSUER", DEFAULT_ISSUER)
    audience = os.environ.get("MCP_JWT_AUDIENCE", DEFAULT_AUDIENCE)
    if not issuer.strip() or not audience.strip():
        raise ValueError("MCP_JWT_ISSUER and MCP_JWT_AUDIENCE must not be blank.")
    # Missing or invalid public keys stop startup; HTTP never falls back to anonymous.
    auth = JWTVerifier(
        public_key=public_key_path.read_text(),
        algorithm="RS256",
        issuer=issuer,
        audience=audience,
        required_scopes=["courses:read"],
    )
    return FastMCP(
        "AdvisorMCP", auth=auth,
        providers=[FileSystemProvider(project_root / "src" / "tools")],
    )


def generate_bearer_token(
    developer_id: str,
    private_key: bytes,
    *,
    hours: int = 24,
    issuer: str = DEFAULT_ISSUER,
    audience: str = DEFAULT_AUDIENCE,
) -> str:
    """Sign an expiring RS256 token using PyJWT, without storing the token."""
    developer_id = developer_id.strip()
    if not developer_id:
        raise ValueError("Developer ID must not be blank.")
    if hours <= 0:
        raise ValueError("Token lifetime must be positive.")
    if not issuer.strip() or not audience.strip():
        raise ValueError("Issuer and audience must not be blank.")
    now = int(datetime.now(timezone.utc).timestamp())
    return jwt.encode(
        {
            "sub": developer_id,
            "client_id": developer_id,
            "iss": issuer,
            "aud": audience,
            "iat": now,
            "exp": now + hours * 3600,
            "jti": str(uuid4()),
            "scope": "courses:read",
        },
        private_key,
        algorithm="RS256",
    )


# Create a bearer token using the existing private key.
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("developer_id")
    parser.add_argument("--private-key", type=Path, default=PROJECT_ROOT / ".auth/private.pem")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--issuer", default=DEFAULT_ISSUER)
    parser.add_argument("--audience", default=DEFAULT_AUDIENCE)
    args = parser.parse_args()
    try:
        token = generate_bearer_token(
            args.developer_id, args.private_key.read_bytes(), hours=args.hours,
            issuer=args.issuer, audience=args.audience,
        )
    except (OSError, ValueError, jwt.exceptions.PyJWTError) as error:
        parser.error(str(error))
    # Output only the token so it can be copied into the client's bearer setting.
    print(token)


if __name__ == "__main__":
    main()
