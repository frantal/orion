"""Market data models and regime classification types."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class MarketRegime(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    EVENT_DRIVEN = "EVENT_DRIVEN"
    UNCERTAIN = "UNCERTAIN"


class MarketContext(BaseModel):
    """Deterministic read of the current market for a symbol."""

    symbol: str
    price: float
    regime: MarketRegime
    directional_bias: str = Field(description="'bullish' | 'bearish' | 'neutral'")
    change_percent: float | None = None
    implied_volatility: float | None = None
    day_range_percent: float | None = None
    notes: list[str] = Field(default_factory=list)
