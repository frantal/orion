"""Probability model: terminal price distribution and payoff vectors.

Terminal underlying price is modelled as lognormal with zero drift (risk-neutral
approximation, r=0) and volatility from the option's implied volatility. This
lets the Quant Engine compute expected value and probability of profit for ANY
strategy through one numeric integration — no LLM involved.
"""

from __future__ import annotations

import numpy as np

from backend.alpaca.models import OptionType
from backend.options.models import StrategyCandidate

DEFAULT_IV = 0.25


def terminal_distribution(
    spot: float,
    iv: float,
    dte_days: int,
    points: int = 401,
    width: float = 4.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(prices, probabilities)`` for the terminal underlying price.

    ``width`` is the number of standard deviations spanned each side.
    """
    t = max(dte_days, 1) / 365.0
    sigma = max(iv, 1e-4)
    vol = sigma * np.sqrt(t)
    z = np.linspace(-width, width, points)
    prices = spot * np.exp(-0.5 * vol**2 + vol * z)
    weights = np.exp(-0.5 * z**2)
    weights /= weights.sum()
    return prices, weights


def payoff_vector(candidate: StrategyCandidate, prices: np.ndarray) -> np.ndarray:
    """Vectorized profit/loss (dollars) across terminal prices for one unit."""
    total = np.zeros_like(prices)
    for leg in candidate.legs:
        c = leg.contract
        if c.option_type is OptionType.CALL:
            intrinsic = np.maximum(prices - c.strike, 0.0)
        else:
            intrinsic = np.maximum(c.strike - prices, 0.0)
        total = total + leg.sign * 100 * intrinsic * leg.ratio
    return total - candidate.cost_basis
