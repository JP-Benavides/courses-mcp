import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from supabase.client import ClientOptions

# Load the project .env regardless of the client's working directory.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

#Retrieve Env Variables 
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_PUBLISHABLE_KEY")


#Create Supabase Client 
supabase: Client = create_client(
    url,
    key,
    options=ClientOptions(
        postgrest_client_timeout=10,
        storage_client_timeout=10,
        schema="public",
    )
)


