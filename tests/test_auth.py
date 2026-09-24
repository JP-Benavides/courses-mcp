import asyncio
import os
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastmcp.server.auth.providers.jwt import JWTVerifier
from starlette.testclient import TestClient

from src.middleware.auth.generate_bearer_token import create_server, generate_bearer_token


@pytest.fixture
def keys():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return (
        key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                          serialization.NoEncryption()),
        key.public_key().public_bytes(serialization.Encoding.PEM,
                                      serialization.PublicFormat.SubjectPublicKeyInfo),
    )


def test_verifier_accepts_generated_token(keys):
    private, public = keys
    verifier = JWTVerifier(public_key=public, algorithm="RS256", issuer="courses-mcp-local",
                           audience="courses-mcp", required_scopes=["courses:read"])
    token = generate_bearer_token("alice", private)
    result = asyncio.run(verifier.verify_token(token))
    assert result is not None
    assert result.client_id == "alice"
    assert result.scopes == ["courses:read"]


@pytest.mark.parametrize("change", [
    {"exp": 1}, {"iss": "wrong"}, {"aud": "wrong"}, {"scope": "other"},
])
def test_verifier_rejects_invalid_claims(keys, change):
    private, public = keys
    claims = jwt.decode(generate_bearer_token("alice", private), options={"verify_signature": False})
    claims.update(change)
    token = jwt.encode(claims, private, algorithm="RS256")
    verifier = JWTVerifier(public_key=public, algorithm="RS256", issuer="courses-mcp-local",
                           audience="courses-mcp", required_scopes=["courses:read"])
    assert asyncio.run(verifier.verify_token(token)) is None


def test_http_requires_valid_token(keys, tmp_path):
    private, public = keys
    key_path = tmp_path / "public.pem"
    key_path.write_bytes(public)
    with patch.dict(os.environ, {"MCP_JWT_PUBLIC_KEY_FILE": str(key_path),
                                 "MCP_JWT_ISSUER": "courses-mcp-local",
                                 "MCP_JWT_AUDIENCE": "courses-mcp"}):
        server = create_server()
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    wrong_token = jwt.encode({"sub": "alice"}, other_key, algorithm="RS256")
    with TestClient(server.http_app()) as client:
        for token in (None, "invalid", wrong_token):
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            assert client.post("/mcp", headers=headers).status_code == 401
        response = client.post("/mcp", headers={
            "Authorization": f"Bearer {generate_bearer_token('alice', private)}",
            "Accept": "application/json, text/event-stream",
        }, json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "test", "version": "1"},
        }})
        assert response.status_code == 200


def test_missing_key_stops_startup(tmp_path):
    with patch.dict(os.environ, {"MCP_JWT_PUBLIC_KEY_FILE": str(tmp_path / "missing.pem")}):
        with pytest.raises(FileNotFoundError):
            create_server()


def test_http_rate_limit_uses_verified_developer(keys, tmp_path, monkeypatch):
    private, public = keys
    key_path = tmp_path / "public.pem"
    key_path.write_bytes(public)
    monkeypatch.setenv("MCP_JWT_PUBLIC_KEY_FILE", str(key_path))
    monkeypatch.setenv("MCP_JWT_ISSUER", "courses-mcp-local")
    monkeypatch.setenv("MCP_JWT_AUDIENCE", "courses-mcp")
    monkeypatch.setenv("MCP_RATE_LIMIT_PER_SECOND", "0.001")
    monkeypatch.setenv("MCP_RATE_LIMIT_BURST", "1")
    server = create_server()
    with TestClient(server.http_app()) as client:
        def initialize(developer):
            return client.post("/mcp", headers={
                "Authorization": f"Bearer {generate_bearer_token(developer, private)}",
                "Accept": "application/json, text/event-stream",
            }, json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2025-06-18", "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            }})

        assert "serverInfo" in initialize("alice").text
        rejected = initialize("alice")
        assert "Rate limit exceeded" in rejected.text
        assert "-32000" in rejected.text
        assert "serverInfo" in initialize("bob").text


@pytest.mark.parametrize("developer,hours", [(" ", 24), ("alice", 0), ("alice", -1)])
def test_invalid_token_inputs(keys, developer, hours):
    with pytest.raises(ValueError):
        generate_bearer_token(developer, keys[0], hours=hours)
