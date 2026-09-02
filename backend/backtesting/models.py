"""Backtesting / replay models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.portfolio.performance import PerformanceStats


class StrategyBacktest(BaseModel):
    """Simulated performance for a single opportunity/strategy."""

    opportunity_id: str
    symbol: str
    strategy: str
    samples: int
    implied_volatility: float | None
    analytic_expected_value: float
    performance: PerformanceStats


class BacktestReport(BaseModel):
    """Aggregate backtest over a set of opportunities."""

    symbol: str
    method: str = "monte_carlo_terminal_distribution"
    disclaimer: str = (
        "Simulated outcomes from a modelled terminal distribution. "
        "Past or simulated results do not guarantee future performance."
    )
    per_strategy: list[StrategyBacktest] = Field(default_factory=list)
    aggregate: PerformanceStats
