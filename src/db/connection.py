from contextlib import contextmanager
from collections.abc import Iterator
import httpx
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client
from supabase.client import ClientOptions
from src.middleware.auth.identity import require_user_token


@contextmanager
def get_supabase() -> Iterator[Client]:
    """Create an isolated client carrying this request's verified user token."""
    # Resolve configuration only when a tool needs the database.
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_PUBLISHABLE_KEY")
    if not url or not key:
        raise ValueError(
            "Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY before using database tools."
        )

    token = require_user_token()
    with httpx.Client(timeout=10) as http_client:
        yield create_client(
            url,
            key,
            options=ClientOptions(
                httpx_client=http_client,
                headers={"Authorization": f"Bearer {token.token}"},
                auto_refresh_token=False,
                persist_session=False,
                postgrest_client_timeout=10,
                storage_client_timeout=10,
                schema="public",
            ),
        )
