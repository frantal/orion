"""Performance Engine.

Deterministic performance statistics from a series of trade P/Ls. Used by the
backtesting/replay engine and by realized-trade reporting. No claim is made that
past or simulated results predict the future.
"""

from __future__ import annotations

import math

from pydantic import BaseModel


class PerformanceStats(BaseModel):
    num_trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    avg_win: float
    avg_loss: float
    expectancy: float
    profit_factor: float | None  # None when there are no losses
    max_drawdown: float
    sharpe: float | None  # per-trade Sharpe approximation; None when undefined


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    var = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var)


def _max_drawdown(pnls: list[float]) -> float:
    """Largest peak-to-trough drop on the cumulative equity curve (positive)."""
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnls:
        equity += p
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return round(max_dd, 2)


def compute_performance(pnls: list[float]) -> PerformanceStats:
    """Compute performance statistics from realized/simulated P/Ls (dollars)."""
    n = len(pnls)
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    total = sum(pnls)
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    std = _std(pnls)

    return PerformanceStats(
        num_trades=n,
        wins=len(wins),
        losses=len(losses),
        win_rate=round(len(wins) / n, 4) if n else 0.0,
        total_pnl=round(total, 2),
        avg_win=round(_mean(wins), 2),
        avg_loss=round(_mean(losses), 2),
        expectancy=round(_mean(pnls), 2),
        profit_factor=round(gross_win / gross_loss, 4) if gross_loss > 0 else None,
        max_drawdown=_max_drawdown(pnls),
        sharpe=round(_mean(pnls) / std, 4) if std > 0 else None,
    )
