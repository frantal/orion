"""Expected value and probability of profit from the terminal distribution."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from backend.options.models import StrategyCandidate
from backend.quant.probability import payoff_vector, terminal_distribution


@dataclass
class ExpectedValueResult:
    expected_value: float
    probability_of_profit: float
    avg_win: float
    avg_loss: float  # negative or zero


def evaluate(candidate: StrategyCandidate, spot: float, iv: float) -> ExpectedValueResult:
    """Integrate the strategy payoff over the terminal distribution."""
    prices, weights = terminal_distribution(spot, iv, candidate.dte)
    pl = payoff_vector(candidate, prices)

    ev = float((pl * weights).sum())
    win = pl > 0
    loss = pl < 0
    pop = float(weights[win].sum())
    avg_win = float((pl[win] * weights[win]).sum() / weights[win].sum()) if win.any() else 0.0
    avg_loss = float((pl[loss] * weights[loss]).sum() / weights[loss].sum()) if loss.any() else 0.0

    return ExpectedValueResult(
        expected_value=round(ev, 4),
        probability_of_profit=round(pop, 4),
        avg_win=round(avg_win, 4),
        avg_loss=round(avg_loss, 4),
    )
