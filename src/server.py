from pathlib import Path
import sys

# Support the package import when this file is launched directly.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider

from src.middleware.auth.config import OAuthConfig
from src.middleware.auth.provider import create_auth
from src.middleware.auth.system_prompt import SYSTEM_PROMPT
from src.middleware.rate_limiter.rate_limiter import create_rate_limiter


def create_server() -> FastMCP:
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    return FastMCP(
        "AdvisorMCP",
        auth=create_auth(OAuthConfig.from_env()),
        middleware=[create_rate_limiter()],
        instructions=SYSTEM_PROMPT,
        providers=[FileSystemProvider(root / "src" / "tools")],
    )


def main():
    create_server().run(transport="http", host="127.0.0.1", port=8000)

if __name__ == "__main__":
    main()
