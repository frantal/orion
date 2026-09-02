"""Tests for the Alpaca CLI-backed client (subprocess mocked — no real CLI)."""

from __future__ import annotations

import json

import pytest

from backend.alpaca.cli_client import AlpacaCLIClient
from backend.alpaca.mcp_adapter import get_adapter
from backend.core.config import Settings


def _cli_settings() -> Settings:
    return Settings(
        _env_file=None,
        ALPACA_API_KEY="k",
        ALPACA_SECRET_KEY="s",
        ALPACA_PAPER_TRADE=True,
        USE_ALPACA_CLI=True,
    )


def test_adapter_selects_cli_client() -> None:
    adapter = get_adapter(_cli_settings())
    assert type(adapter._client).__name__ == "AlpacaCLIClient"


@pytest.mark.asyncio
async def test_cli_get_account_calls_api(monkeypatch) -> None:
    client = AlpacaCLIClient(_cli_settings())
    captured = {}

    async def fake_run(*args):
        captured["args"] = args
        return json.dumps({"status": "ACTIVE", "equity": "100000"})

    monkeypatch.setattr(client, "_run", fake_run)
    acct = await client.get_account()
    assert acct["status"] == "ACTIVE"
    assert captured["args"] == ("api", "GET", "/v2/account")


@pytest.mark.asyncio
async def test_cli_submit_order_builds_body(monkeypatch) -> None:
    client = AlpacaCLIClient(_cli_settings())
    captured = {}

    async def fake_run(*args):
        captured["args"] = args
        return json.dumps({"id": "abc", "status": "new"})

    monkeypatch.setattr(client, "_run", fake_run)
    body = {"symbol": "SPY", "qty": "1", "side": "buy", "type": "limit"}
    result = await client.submit_order(body)
    assert result["status"] == "new"
    args = captured["args"]
    assert args[0:3] == ("api", "POST", "/v2/orders")
    assert "--body" in args
    sent = json.loads(args[args.index("--body") + 1])
    assert sent["symbol"] == "SPY"


@pytest.mark.asyncio
async def test_cli_get_orders_query(monkeypatch) -> None:
    client = AlpacaCLIClient(_cli_settings())
    captured = {}

    async def fake_run(*args):
        captured["args"] = args
        return "[]"

    monkeypatch.setattr(client, "_run", fake_run)
    out = await client.get_orders(status="all", limit=25)
    assert out == []
    args = captured["args"]
    assert "--query" in args
    assert "status=all&limit=25&nested=true" in args
