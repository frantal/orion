"""Tests for the Alpaca adapter and Phase 2 endpoints (no live calls)."""

from __future__ import annotations

from datetime import date, datetime, timezone

import httpx
import pytest

from backend.alpaca.models import (
    Account,
    Clock,
    Greeks,
    OptionChain,
    OptionContract,
    OptionType,
    StockQuote,
    StockSnapshot,
)
from backend.alpaca.mcp_adapter import AlpacaAdapter, parse_occ_symbol


def test_parse_occ_symbol_call() -> None:
    underlying, expiration, opt_type, strike = parse_occ_symbol("SPY260918C00540000")
    assert underlying == "SPY"
    assert expiration == date(2026, 9, 18)
    assert opt_type is OptionType.CALL
    assert strike == 540.0


def test_parse_occ_symbol_put() -> None:
    underlying, expiration, opt_type, strike = parse_occ_symbol("AAPL260116P00185500")
    assert underlying == "AAPL"
    assert opt_type is OptionType.PUT
    assert strike == 185.5


def test_parse_occ_symbol_malformed() -> None:
    with pytest.raises(ValueError):
        parse_occ_symbol("SPY")


def test_parse_option_snapshot() -> None:
    snap = {
        "latestQuote": {"bp": 5.2, "ap": 5.4, "bs": 10, "as": 12},
        "latestTrade": {"p": 5.3},
        "dailyBar": {"v": 1500},
        "greeks": {"delta": 0.55, "gamma": 0.03, "theta": -0.04, "vega": 0.10, "rho": 0.02},
        "impliedVolatility": 0.18,
    }
    contract = AlpacaAdapter._parse_option_snapshot("SPY260918C00540000", snap)
    assert contract is not None
    assert contract.strike == 540.0
    assert contract.bid == 5.2
    assert contract.ask == 5.4
    assert contract.mid == 5.3
    assert contract.implied_volatility == 0.18
    assert contract.greeks.delta == 0.55


def test_option_contract_spread_percent() -> None:
    c = OptionContract(
        symbol="SPY260918C00540000",
        underlying="SPY",
        expiration=date(2026, 9, 18),
        strike=540.0,
        option_type=OptionType.CALL,
        bid=1.00,
        ask=1.10,
    )
    assert c.mid == 1.05
    assert c.spread == pytest.approx(0.10, abs=1e-6)
    assert c.spread_percent == pytest.approx(9.5238, abs=1e-3)


def test_stock_snapshot_change() -> None:
    s = StockSnapshot(symbol="SPY", price=110.0, prev_close=100.0)
    assert s.change == 10.0
    assert s.change_percent == 10.0


# --- Endpoint tests with a fake adapter (no live Alpaca) ---


class _FakeAdapter:
    async def get_account(self) -> Account:
        return Account(
            account_number="PA123",
            status="ACTIVE",
            currency="USD",
            equity=100000.0,
            cash=100000.0,
            buying_power=400000.0,
            portfolio_value=100000.0,
            options_buying_power=100000.0,
            options_trading_level=2,
        )

    async def get_clock(self) -> Clock:
        now = datetime.now(timezone.utc)
        return Clock(timestamp=now, is_open=False, next_open=now, next_close=now)

    async def get_market_snapshot(self, symbol: str) -> StockSnapshot:
        return StockSnapshot(symbol=symbol, price=761.85, prev_close=760.0)

    async def get_stock_quote(self, symbol: str) -> StockQuote:
        return StockQuote(
            symbol=symbol,
            bid=761.80,
            ask=761.90,
            bid_size=1,
            ask_size=1,
            timestamp=datetime.now(timezone.utc),
        )

    async def get_option_chain(self, underlying: str, **kwargs) -> OptionChain:
        c = OptionContract(
            symbol="SPY260918C00540000",
            underlying="SPY",
            expiration=date(2026, 9, 18),
            strike=540.0,
            option_type=OptionType.CALL,
            bid=1.0,
            ask=1.1,
            greeks=Greeks(delta=0.5),
        )
        return OptionChain(underlying=underlying, contracts=[c])


@pytest.fixture()
def client(monkeypatch):
    from backend import app as app_module
    from backend.api import routes

    monkeypatch.setattr(routes, "_require_alpaca", lambda: _FakeAdapter())
    app = app_module.create_app()
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_account_endpoint(client) -> None:
    async with client:
        resp = await client.get("/api/account")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ACTIVE"
    assert body["buying_power"] == 400000.0


@pytest.mark.asyncio
async def test_market_endpoint(client) -> None:
    async with client:
        resp = await client.get("/api/market/SPY")
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "SPY"
    assert body["price"] == 761.85
    assert body["mid"] == pytest.approx(761.85, abs=0.1)


@pytest.mark.asyncio
async def test_options_endpoint(client) -> None:
    async with client:
        resp = await client.get("/api/options/SPY")
    assert resp.status_code == 200
    body = resp.json()
    assert body["underlying"] == "SPY"
    assert body["count"] == 1
    assert body["contracts"][0]["strike"] == 540.0
