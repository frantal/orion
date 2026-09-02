"""Quant Engine data models.

These carry the deterministic outputs of the Quant Engine. An
:class:`Opportunity` is the Alpha Engine object (section 11 of the spec): a
candidate plus its quantitative metrics, scores, regime and invalidation notes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from backend.market.models import MarketRegime
from backend.options.models import StrategyCandidate


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    """Clamp a value to ``[low, high]``."""
    return max(low, min(high, value))


class QuantMetrics(BaseModel):
    """Deterministic quantitative metrics for a candidate."""

    probability_of_profit: float
    expected_value: float
    risk_reward: float
    avg_win: float
    avg_loss: float
    liquidity_score: float
    volatility_score: float
    implied_volatility: float | None
    alpha_score: float
    risk_score: float
    confidence: float


class Opportunity(BaseModel):
    """The Alpha Engine opportunity object."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str
    candidate: StrategyCandidate
    metrics: QuantMetrics
    market_regime: MarketRegime
    catalysts: list[str] = Field(default_factory=list)
    invalidation_conditions: list[str] = Field(default_factory=list)

    # --- Convenience accessors (flatten for scoring/risk/API) ---
    @property
    def strategy(self) -> str:
        return self.candidate.strategy.value

    @property
    def alpha_score(self) -> float:
        return self.metrics.alpha_score

    @property
    def risk_score(self) -> float:
        return self.metrics.risk_score

    @property
    def liquidity_score(self) -> float:
        return self.metrics.liquidity_score

    @property
    def expected_value(self) -> float:
        return self.metrics.expected_value

    @property
    def risk_reward(self) -> float:
        return self.metrics.risk_reward

    @property
    def max_loss(self) -> float:
        return self.candidate.max_loss

    @property
    def max_profit(self) -> float | None:
        return self.candidate.max_profit
