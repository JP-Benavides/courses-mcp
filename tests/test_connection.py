from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.db.connection import get_supabase


@pytest.fixture(autouse=True)
def config(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "test-key")
    with patch("src.db.connection.load_dotenv"):
        yield


def test_missing_configuration_fails_only_on_use(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL")
    with pytest.raises(ValueError, match="SUPABASE_URL"), get_supabase():
        pass


def test_missing_identity_cannot_query_database():
    with patch("src.middleware.auth.identity.get_access_token", return_value=None):
        with pytest.raises(ValueError, match="authenticated"), get_supabase():
            pass


def test_clients_are_isolated_and_transport_closes_on_success_and_failure():
    with patch("src.db.connection.require_user_token") as token, patch("src.db.connection.create_client") as create:
        create.side_effect = [MagicMock(), MagicMock()]
        token.return_value = SimpleNamespace(token="alice-token")
        with get_supabase() as first:
            options = create.call_args.kwargs["options"]
            assert options.headers["Authorization"] == "Bearer alice-token"
            assert not options.auto_refresh_token
            assert not options.persist_session
            assert not options.httpx_client.is_closed
        assert options.httpx_client.is_closed
        token.return_value = SimpleNamespace(token="bob-token")
        with pytest.raises(RuntimeError, match="query failed"):
            with get_supabase() as second:
                assert first is not second
                second_options = create.call_args.kwargs["options"]
                assert second_options.headers["Authorization"] == "Bearer bob-token"
                assert options.headers["Authorization"] == "Bearer alice-token"
                raise RuntimeError("query failed")
        assert second_options.httpx_client.is_closed


def test_real_client_forwards_token_to_postgrest():
    with patch("src.db.connection.require_user_token", return_value=SimpleNamespace(token="user-token")):
        with get_supabase() as client:
            def respond(request, **kwargs):
                assert request.headers["Authorization"] == "Bearer user-token"
                assert request.headers["apikey"] == "test-key"
                return httpx.Response(200, json=[], request=request)
            with patch.object(client.postgrest.session, "send", side_effect=respond) as send:
                assert client.table("courses").select("code").execute().data == []
                send.assert_called_once()
