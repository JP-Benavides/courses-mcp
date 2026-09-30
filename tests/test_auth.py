import asyncio
import time
from unittest.mock import MagicMock, patch

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastmcp.server.auth import RemoteAuthProvider
from pydantic import AnyHttpUrl
from starlette.testclient import TestClient

from src.middleware.auth.config import OAuthConfig
from src.middleware.auth.provider import OAUTH_SCOPES, SupabaseUserVerifier, create_auth
from src.server import create_server
from src.db.connection import create_client as real_create_client

ISSUER = "https://example.supabase.co/auth/v1"
RESOURCE = "https://mcp.example.com/mcp"
ALICE = "11111111-1111-4111-8111-111111111111"
BOB = "22222222-2222-4222-8222-222222222222"


@pytest.fixture
def keys():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key, key.public_key().public_bytes(serialization.Encoding.PEM,
                                            serialization.PublicFormat.SubjectPublicKeyInfo)


def claims(**changes):
    return {"sub": ALICE, "iss": ISSUER, "aud": RESOURCE,
            "exp": int(time.time()) + 600, "role": "authenticated",
            "is_anonymous": False, "client_id": "chatgpt", **changes}


def verifier(public):
    return SupabaseUserVerifier(public_key=public, algorithm="RS256", issuer=ISSUER,
                                audience=RESOURCE)


@pytest.mark.parametrize("audience", [RESOURCE, ["authenticated", RESOURCE]])
def test_accepts_oauth_user_without_scope_claim(keys, audience):
    token = jwt.encode(claims(aud=audience, client_id="dynamic-client"), keys[0], algorithm="RS256")
    result = asyncio.run(verifier(keys[1]).verify_token(token))
    assert result.claims["sub"] == ALICE
    assert result.client_id == "dynamic-client"


@pytest.mark.parametrize("change", [
    {"exp": 10**400}, {"nbf": 10**400}, {"exp": 1}, {"exp": None}, {"exp": True}, {"exp": "tomorrow"},
    {"nbf": time.time() + 3600}, {"nbf": True}, {"nbf": "later"},
    {"iss": "wrong"}, {"aud": "authenticated"}, {"aud": None},
    {"sub": "alice"}, {"sub": None}, {"role": "service_role"},
    {"is_anonymous": True}, {"is_anonymous": None},
    {"client_id": None}, {"client_id": ""}, {"client_id": "  "},
    {"client_id": " client"}, {"client_id": "client\n"}, {"client_id": ["chatgpt"]},
])
def test_rejects_invalid_claims(keys, change):
    token = jwt.encode(claims(**change), keys[0], algorithm="RS256")
    assert asyncio.run(verifier(keys[1]).verify_token(token)) is None


def test_rejects_missing_expiration(keys):
    payload = claims()
    del payload["exp"]
    assert asyncio.run(verifier(keys[1]).verify_token(jwt.encode(payload, keys[0], algorithm="RS256"))) is None


def test_config_does_not_require_static_oauth_clients(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("MCP_PUBLIC_URL", "https://mcp.example.com")
    monkeypatch.delenv("MCP_OAUTH_CLIENT_IDS", raising=False)
    assert OAuthConfig.from_env().resource == RESOURCE


def test_http_discovery_authentication_and_user_rate_limits(keys, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("MCP_PUBLIC_URL", "https://mcp.example.com")
    monkeypatch.setenv("MCP_RATE_LIMIT_PER_SECOND", "0.001")
    monkeypatch.setenv("MCP_RATE_LIMIT_BURST", "1")
    auth = RemoteAuthProvider(token_verifier=verifier(keys[1]),
                              authorization_servers=[AnyHttpUrl(ISSUER)],
                              base_url="https://mcp.example.com", scopes_supported=OAUTH_SCOPES,
                              challenge_scopes=OAUTH_SCOPES)
    with patch("src.server.create_auth", return_value=auth):
        server = create_server()
    with TestClient(server.http_app()) as client:
        response = client.post("/mcp")
        assert response.status_code == 401
        assert 'resource_metadata=' in response.headers['www-authenticate']
        metadata_url = response.headers['www-authenticate'].split('resource_metadata="')[1].split('"')[0]
        metadata = client.get(metadata_url).json()
        assert metadata["resource"] == RESOURCE
        assert metadata["authorization_servers"] == [ISSUER]
        assert metadata["scopes_supported"] == OAUTH_SCOPES
        wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        for token in ["invalid", jwt.encode(claims(), wrong_key, algorithm="RS256")]:
            assert client.post("/mcp", headers={"Authorization": f"Bearer {token}"}).status_code == 401

        def initialize(subject, **extra):
            token = jwt.encode(claims(sub=subject, **extra), keys[0], algorithm="RS256")
            return client.post("/mcp", headers={"Authorization": f"Bearer {token}",
                "Accept": "application/json, text/event-stream"}, json={
                "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                    "protocolVersion": "2025-06-18", "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"}}})
        assert "serverInfo" in initialize(ALICE).text
        assert "Rate limit exceeded" in initialize(ALICE, jti="renewed-token").text
        assert "serverInfo" in initialize(BOB).text


def test_authenticated_http_tool_forwards_dynamic_client_user_token(keys, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "test-key")
    monkeypatch.setenv("MCP_PUBLIC_URL", "https://mcp.example.com")
    monkeypatch.setenv("MCP_RATE_LIMIT_PER_SECOND", "100")
    monkeypatch.setenv("MCP_RATE_LIMIT_BURST", "100")
    token = jwt.encode(claims(aud=["authenticated", RESOURCE], client_id="new-dcr-client"),
                       keys[0], algorithm="RS256")
    requests = []

    def create_client_with_mocked_network(*args, **kwargs):
        db_client = real_create_client(*args, **kwargs)

        def respond(request, **unused):
            requests.append(request)
            return httpx.Response(200, json=[], request=request)

        db_client.postgrest.session.send = MagicMock(side_effect=respond)
        return db_client

    auth = RemoteAuthProvider(token_verifier=verifier(keys[1]),
                              authorization_servers=[AnyHttpUrl(ISSUER)],
                              base_url="https://mcp.example.com", scopes_supported=["openid"],
                              challenge_scopes=["openid"])
    with patch("src.server.create_auth", return_value=auth), \
         patch("src.db.connection.create_client", side_effect=create_client_with_mocked_network), \
         patch("src.db.connection.load_dotenv"):
        server = create_server()
        with TestClient(server.http_app()) as client:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json, text/event-stream",
            }
            initialized = client.post("/mcp", headers=headers, json={
                "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                    "protocolVersion": "2025-06-18", "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"}}})
            assert initialized.status_code == 200, initialized.text
            headers["Mcp-Session-Id"] = initialized.headers["mcp-session-id"]
            response = client.post("/mcp", headers=headers, json={
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                     "params": {"name": "list_programs", "arguments": {}}})

    assert response.status_code == 200, response.text
    assert '"result"' in response.text
    assert len(requests) == 1
    assert requests[0].headers["authorization"] == f"Bearer {token}"
    assert requests[0].headers["apikey"] == "test-key"
    assert requests[0].url.path.endswith("/rest/v1/courses")


@pytest.mark.parametrize("name,value", [
    ("SUPABASE_URL", "http://example.com"), ("MCP_PUBLIC_URL", "https://example.com/path"),
    ("MCP_PUBLIC_URL", "https://user:password@example.com"),
    ("MCP_JWT_ALGORITHM", "HS256"),
])
def test_invalid_configuration(name, value, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("MCP_PUBLIC_URL", "https://mcp.example.com")
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError):
        OAuthConfig.from_env()


def test_provider_uses_resource_audience_and_supabase_jwks():
    auth = create_auth(OAuthConfig("https://example.supabase.co", "https://mcp.example.com",
                                   "ES256"))
    assert auth.token_verifier.audience == RESOURCE
    assert auth.token_verifier.issuer == ISSUER
    assert auth.token_verifier.jwks_uri == ISSUER + "/.well-known/jwks.json"


def test_tools_advertise_oauth_and_read_only(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("MCP_PUBLIC_URL", "https://mcp.example.com")
    async def run():
        from fastmcp import Client
        async with Client(create_server()) as client:
            tools = await client.list_tools()
            assert len(tools) == 9
            for tool in tools:
                assert tool.meta["securitySchemes"] == [{"type": "oauth2", "scopes": OAUTH_SCOPES}]
                assert tool.annotations.read_only_hint is True
    asyncio.run(run())


def test_default_es256_verifies_signed_user_token():
    private = ec.generate_private_key(ec.SECP256R1())
    public = private.public_key().public_bytes(serialization.Encoding.PEM,
                                               serialization.PublicFormat.SubjectPublicKeyInfo)
    validator = SupabaseUserVerifier(public_key=public, algorithm="ES256", issuer=ISSUER,
                                     audience=RESOURCE)
    token = jwt.encode(claims(aud=["authenticated", RESOURCE]), private, algorithm="ES256")
    assert asyncio.run(validator.verify_token(token)).claims["sub"] == ALICE
