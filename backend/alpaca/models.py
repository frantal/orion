"""Domain models for Alpaca data.

These are the *internal* shapes ORION works with — deliberately decoupled from
Alpaca's raw JSON so the rest of the codebase never depends on wire format.
Parsing from raw payloads lives in :mod:`backend.alpaca.mcp_adapter`.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class OptionType(str, Enum):
    CALL = "call"
    PUT = "put"


class Account(BaseModel):
    """Trading account snapshot (paper)."""

    account_number: str
    status: str
    currency: str
    equity: float
    cash: float
    buying_power: float
    portfolio_value: float
    options_buying_power: float | None = None
    options_trading_level: int | None = None
    pattern_day_trader: bool = False
    trading_blocked: bool = False


class Clock(BaseModel):
    """Market clock."""

    timestamp: datetime
    is_open: bool
    next_open: datetime
    next_close: datetime


class StockQuote(BaseModel):
    """Latest NBBO quote for a stock."""

    symbol: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    timestamp: datetime

    @property
    def mid(self) -> float:
        if self.bid > 0 and self.ask > 0:
            return round((self.bid + self.ask) / 2, 4)
        return self.ask or self.bid


class StockSnapshot(BaseModel):
    """Aggregated market snapshot used by Market Intelligence."""

    symbol: str
    price: float
    prev_close: float | None = None
    day_open: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    day_volume: float | None = None

    @property
    def change(self) -> float | None:
        if self.prev_close:
            return round(self.price - self.prev_close, 4)
        return None

    @property
    def change_percent(self) -> float | None:
        if self.prev_close:
            return round((self.price - self.prev_close) / self.prev_close * 100, 4)
        return None


class Greeks(BaseModel):
    """Option Greeks (may be partially populated depending on data feed)."""

    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    rho: float | None = None


class OptionContract(BaseModel):
    """A single option contract snapshot."""

    symbol: str
    underlying: str
    expiration: date
    strike: float
    option_type: OptionType
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    volume: float | None = None
    open_interest: float | None = None
    implied_volatility: float | None = None
    greeks: Greeks = Field(default_factory=Greeks)

    @property
    def mid(self) -> float | None:
        if self.bid and self.ask and self.bid > 0 and self.ask > 0:
            return round((self.bid + self.ask) / 2, 4)
        return self.last

    @property
    def spread(self) -> float | None:
        if self.bid is not None and self.ask is not None and self.ask > 0:
            return round(self.ask - self.bid, 4)
        return None

    @property
    def spread_percent(self) -> float | None:
        mid = self.mid
        spread = self.spread
        if mid and spread is not None and mid > 0:
            return round(spread / mid * 100, 4)
        return None


class OptionChain(BaseModel):
    """Option chain for an underlying."""

    underlying: str
    contracts: list[OptionContract] = Field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.contracts)

    def calls(self) -> list[OptionContract]:
        return [c for c in self.contracts if c.option_type is OptionType.CALL]

    def puts(self) -> list[OptionContract]:
        return [c for c in self.contracts if c.option_type is OptionType.PUT]

    def expirations(self) -> list[date]:
        return sorted({c.expiration for c in self.contracts})


class Position(BaseModel):
    """An open position (paper)."""

    symbol: str
    asset_class: str
    qty: float
    side: str
    avg_entry_price: float | None = None
    market_value: float | None = None
    cost_basis: float | None = None
    unrealized_pl: float | None = None

