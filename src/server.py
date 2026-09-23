from pathlib import Path
import sys
import os

# Support the package import when this file is launched directly.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.providers import FileSystemProvider

def create_server() -> FastMCP:
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env")
    public_key_path = Path(os.environ.get("MCP_JWT_PUBLIC_KEY_FILE", ".auth/public.pem"))
    if not public_key_path.is_absolute():
        public_key_path = project_root / public_key_path
    issuer = os.environ.get("MCP_JWT_ISSUER", "courses-mcp-local")
    audience = os.environ.get("MCP_JWT_AUDIENCE", "courses-mcp")
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
        providers=[FileSystemProvider(Path(__file__).parent / "tools")],
    )


def main():
    create_server().run(transport="http", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
