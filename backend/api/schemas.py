"""Pydantic request/response schemas for the ORION API."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class CheckResult(BaseModel):
    """A single diagnostic check result."""

    name: str
    ok: bool
    detail: str


class HealthResponse(BaseModel):
    """Response for ``GET /api/health``."""

    status: str = Field(description="'ok' when all checks pass, else 'degraded'")
    version: str
    demo_mode: bool
    paper_trading: bool
    checks: list[CheckResult]


class AccountResponse(BaseModel):
    """Response for ``GET /api/account``."""

    account_number: str
    status: str
    currency: str
    equity: float
    cash: float
    buying_power: float
    portfolio_value: float
    options_buying_power: float | None = None
    options_trading_level: int | None = None
    pattern_day_trader: bool
    trading_blocked: bool


class ClockResponse(BaseModel):
    """Response for ``GET /api/clock``."""

    timestamp: datetime
    is_open: bool
    next_open: datetime
    next_close: datetime


class MarketResponse(BaseModel):
    """Response for ``GET /api/market/{symbol}``."""

    symbol: str
    price: float
    bid: float
    ask: float
    mid: float
    change: float | None = None
    change_percent: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    day_volume: float | None = None


class GreeksResponse(BaseModel):
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    rho: float | None = None


class OptionContractResponse(BaseModel):
    symbol: str
    underlying: str
    expiration: date
    strike: float
    option_type: str
    bid: float | None = None
    ask: float | None = None
    mid: float | None = None
    last: float | None = None
    volume: float | None = None
    open_interest: float | None = None
    implied_volatility: float | None = None
    spread_percent: float | None = None
    greeks: GreeksResponse


class OptionChainResponse(BaseModel):
    """Response for ``GET /api/options/{symbol}``."""

    underlying: str
    count: int
    expirations: list[date]
    contracts: list[OptionContractResponse]


class RegimeResponse(BaseModel):
    """Market regime context."""

    symbol: str
    price: float
    regime: str
    directional_bias: str
    change_percent: float | None = None
    implied_volatility: float | None = None
    notes: list[str] = Field(default_factory=list)


class LegResponse(BaseModel):
    symbol: str
    strike: float
    option_type: str
    action: str


class SizingResponse(BaseModel):
    contracts: int
    max_position_risk: float
    total_max_loss: float
    executable: bool
    reason: str | None = None


class RiskVerdictResponse(BaseModel):
    status: str
    reasons: list[str] = Field(default_factory=list)
    sizing: SizingResponse | None = None


class OpportunityResponse(BaseModel):
    """A scored opportunity with its Risk Governor verdict."""

    id: str
    symbol: str
    strategy: str
    expiration: date
    dte: int
    legs: list[LegResponse]
    entry_price: float
    net_premium: float
    max_profit: float | None = None
    max_loss: float
    breakevens: list[float]
    probability_of_profit: float
    expected_value: float
    risk_reward: float
    liquidity_score: float
    volatility_score: float
    alpha_score: float
    risk_score: float
    confidence: float
    implied_volatility: float | None = None
    market_regime: str
    invalidation_conditions: list[str]
    risk_governor: RiskVerdictResponse


class OpportunitiesResponse(BaseModel):
    """Response for ``GET /api/opportunities/{symbol}``."""

    symbol: str
    regime: RegimeResponse
    candidates_considered: int
    qualified: int
    opportunities: list[OpportunityResponse]


class AnalyzeRequest(BaseModel):
    """Body for ``POST /api/analyze``."""

    opportunity_id: str
    language: str = "en"


class DecideRequest(BaseModel):
    """Body for ``POST /api/decision``."""

    opportunity_id: str
    language: str = "en"


class ExecuteRequest(BaseModel):
    """Body for ``POST /api/execute``. Execution requires explicit confirmation."""

    opportunity_id: str
    confirm: bool = False


class OrderResultResponse(BaseModel):
    client_order_id: str
    status: str
    broker_order_id: str | None = None
    detail: str = ""


class PositionResponse(BaseModel):
    symbol: str
    asset_class: str
    qty: float
    side: str
    market_value: float | None = None
    unrealized_pl: float | None = None


class BacktestRequest(BaseModel):
    """Body for ``POST /api/backtest``."""

    symbol: str
    samples: int = 2000
    limit: int = 5


