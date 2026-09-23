import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client
from supabase.client import ClientOptions


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Create the database client on first use and reuse it on later calls."""
    # Resolve configuration only when a tool needs the database.
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_PUBLISHABLE_KEY")
    if not url or not key:
        raise ValueError(
            "Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY before using database tools."
        )

    return create_client(
        url,
        key,
        options=ClientOptions(
            postgrest_client_timeout=10,
            storage_client_timeout=10,
            schema="public",
        ),
    )
