"""Demo data adapter — a self-contained, offline Alpaca stand-in.

When ``USE_DEMO_DATA=true`` ORION runs with a deterministic, synthetic market
(Black-Scholes priced option chain) so the full decision pipeline and dashboard
work with NO credentials and NO network. It never places a real order.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from typing import Any

from backend.alpaca.mcp_adapter import AlpacaAdapter
from backend.alpaca.models import (
    Account,
    Clock,
    Greeks,
    OptionChain,
    OptionContract,
    OptionType,
    Position,
    StockQuote,
    StockSnapshot,
)
from backend.core.config import Settings, get_settings

DEMO_SPOT = 545.0
DEMO_PREV_CLOSE = 542.0  # +0.55% -> mildly bullish regime
DEMO_UNDERLYING = "SPY"
RISK_FREE = 0.0


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _bs(spot: float, strike: float, t: float, sigma: float, is_call: bool) -> tuple[float, float]:
    """Return (price, delta) under Black-Scholes with r=0."""
    if t <= 0 or sigma <= 0:
        intrinsic = max(spot - strike, 0.0) if is_call else max(strike - spot, 0.0)
        return intrinsic, 0.0
    d1 = (math.log(spot / strike) + 0.5 * sigma**2 * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    if is_call:
        price = spot * _norm_cdf(d1) - strike * _norm_cdf(d2)
        delta = _norm_cdf(d1)
    else:
        price = strike * _norm_cdf(-d2) - spot * _norm_cdf(-d1)
        delta = _norm_cdf(d1) - 1.0
    return max(price, 0.0), delta


def _occ(underlying: str, expiration: date, is_call: bool, strike: float) -> str:
    return (
        f"{underlying}{expiration.strftime('%y%m%d')}"
        f"{'C' if is_call else 'P'}{int(round(strike * 1000)):08d}"
    )


class DemoAdapter(AlpacaAdapter):
    """Offline adapter serving a deterministic synthetic market."""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(settings or get_settings())

    @property
    def configured(self) -> bool:
        return True

    @property
    def paper_trading(self) -> bool:
        return True

    async def get_account(self) -> Account:
        return Account(
            account_number="DEMO0001",
            status="ACTIVE",
            currency="USD",
            equity=100_000.0,
            cash=100_000.0,
            buying_power=200_000.0,
            portfolio_value=100_000.0,
            options_buying_power=100_000.0,
            options_trading_level=3,
        )

    async def get_clock(self) -> Clock:
        now = datetime.now(timezone.utc)
        return Clock(timestamp=now, is_open=True, next_open=now, next_close=now)

    async def get_stock_quote(self, symbol: str) -> StockQuote:
        return StockQuote(
            symbol=symbol.upper(),
            bid=DEMO_SPOT - 0.02,
            ask=DEMO_SPOT + 0.02,
            bid_size=100,
            ask_size=100,
            timestamp=datetime.now(timezone.utc),
        )

    async def get_market_snapshot(self, symbol: str) -> StockSnapshot:
        return StockSnapshot(
            symbol=symbol.upper(),
            price=DEMO_SPOT,
            prev_close=DEMO_PREV_CLOSE,
            day_open=DEMO_PREV_CLOSE + 0.5,
            day_high=DEMO_SPOT + 1.5,
            day_low=DEMO_PREV_CLOSE - 1.0,
            day_volume=68_000_000,
        )

    async def get_option_chain(
        self,
        underlying: str,
        expiration_gte: date | None = None,
        expiration_lte: date | None = None,
        strike_gte: float | None = None,
        strike_lte: float | None = None,
    ) -> OptionChain:
        underlying = underlying.upper()
        today = date.today()
        contracts: list[OptionContract] = []
        for dte in (16, 30, 44):
            expiration = today + timedelta(days=dte)
            if expiration_gte and expiration < expiration_gte:
                continue
            if expiration_lte and expiration > expiration_lte:
                continue
            t = dte / 365.0
            for offset in range(-12, 13):
                strike = round(DEMO_SPOT + offset, 0)
                if strike_gte and strike < strike_gte:
                    continue
                if strike_lte and strike > strike_lte:
                    continue
                sigma = 0.15 + 0.04 * abs(strike - DEMO_SPOT) / DEMO_SPOT
                for is_call in (True, False):
                    contracts.append(self._contract(underlying, expiration, strike, sigma, t, is_call))
        return OptionChain(underlying=underlying, contracts=contracts)

    @staticmethod
    def _contract(
        underlying: str, expiration: date, strike: float, sigma: float, t: float, is_call: bool
    ) -> OptionContract:
        # Demo edge: price options slightly below the reported IV so the modelled
        # distribution (which uses the reported IV) gives long premium positive EV.
        price, delta = _bs(DEMO_SPOT, strike, t, sigma * 0.90, is_call)
        spread = max(0.03, price * 0.02)
        bid = max(0.01, round(price - spread / 2, 2))
        ask = round(price + spread / 2, 2)
        distance = abs(strike - DEMO_SPOT)
        return OptionContract(
            symbol=_occ(underlying, expiration, is_call, strike),
            underlying=underlying,
            expiration=expiration,
            strike=strike,
            option_type=OptionType.CALL if is_call else OptionType.PUT,
            bid=bid,
            ask=ask,
            last=round((bid + ask) / 2, 2),
            volume=max(20.0, 800.0 - distance * 40.0),
            open_interest=max(100.0, 3000.0 - distance * 120.0),
            implied_volatility=round(sigma, 4),
            greeks=Greeks(delta=round(delta, 4)),
        )

    async def get_positions(self) -> list[Position]:
        return []

    async def get_orders(self, status: str = "all", limit: int = 50) -> list[dict[str, Any]]:
        return []

    async def submit_order(self, body: dict[str, Any]) -> dict[str, Any]:
        # Demo never reaches a real broker; the executor simulates in DEMO_MODE.
        return {"id": f"demo-{body.get('client_order_id', 'order')}", "status": "accepted"}

    async def health_check(self) -> dict[str, Any]:
        return {
            "account": {"ok": True, "detail": "DEMO account (synthetic)"},
            "clock": {"ok": True, "detail": "market OPEN (demo)"},
            "spy_quote": {"ok": True, "detail": f"{DEMO_UNDERLYING} mid={DEMO_SPOT}"},
            "spy_options": {"ok": True, "detail": "synthetic chain"},
        }
