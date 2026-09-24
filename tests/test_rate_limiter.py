import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp.server.middleware import MiddlewareContext
from fastmcp.server.middleware.rate_limiting import RateLimitError

from src.middleware.rate_limiter.rate_limiter import create_rate_limiter

MODULE = "src.middleware.rate_limiter.rate_limiter"
CLOCK = "fastmcp.server.middleware.rate_limiting.time.time"


def test_burst_refill_and_developer_isolation(monkeypatch):
    monkeypatch.setenv("MCP_RATE_LIMIT_PER_SECOND", "1")
    monkeypatch.setenv("MCP_RATE_LIMIT_BURST", "2")

    async def run():
        limiter = create_rate_limiter()
        context = MiddlewareContext(message=None, method="tools/call")
        next_call = AsyncMock(return_value="ok")
        with patch(CLOCK, return_value=100) as clock, patch(MODULE + ".get_access_token") as token:
            token.return_value = SimpleNamespace(client_id="alice", token="first")
            assert await limiter.on_request(context, next_call) == "ok"
            await limiter.on_request(context, next_call)
            # A replacement token must not reset the developer's allowance.
            token.return_value = SimpleNamespace(client_id="alice", token="replacement")
            with pytest.raises(RateLimitError):
                await limiter.on_request(context, next_call)
            assert next_call.await_count == 2
            token.return_value = SimpleNamespace(client_id="bob")
            await limiter.on_request(context, next_call)
            token.return_value = SimpleNamespace(client_id="alice")
            clock.return_value = 101
            await limiter.on_request(context, next_call)
            with pytest.raises(RateLimitError):
                await limiter.on_request(context, next_call)

    asyncio.run(run())


def test_concurrent_requests_cannot_exceed_burst(monkeypatch):
    monkeypatch.setenv("MCP_RATE_LIMIT_BURST", "3")

    async def run():
        limiter = create_rate_limiter()
        context = MiddlewareContext(message=None, method="tools/list")
        next_call = AsyncMock(return_value="ok")
        with patch(CLOCK, return_value=100), patch(MODULE + ".get_access_token", return_value=None):
            results = await asyncio.gather(
                *(limiter.on_request(context, next_call) for _ in range(10)),
                return_exceptions=True,
            )
        assert results.count("ok") == 3
        assert sum(isinstance(r, RateLimitError) for r in results) == 7

    asyncio.run(run())


@pytest.mark.parametrize("name,value", [
    ("MCP_RATE_LIMIT_PER_SECOND", "0"), ("MCP_RATE_LIMIT_PER_SECOND", "-1"),
    ("MCP_RATE_LIMIT_PER_SECOND", "nan"), ("MCP_RATE_LIMIT_PER_SECOND", "inf"),
    ("MCP_RATE_LIMIT_PER_SECOND", "oops"), ("MCP_RATE_LIMIT_BURST", "0"),
    ("MCP_RATE_LIMIT_BURST", "-1"), ("MCP_RATE_LIMIT_BURST", "1.5"),
])
def test_invalid_configuration(name, value, monkeypatch):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError):
        create_rate_limiter()
