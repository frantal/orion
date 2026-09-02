"""Aggregate Greeks for a strategy candidate.

Greeks come from Alpaca per-contract; here we net them across legs (signed by
buy/sell) to describe the position's overall exposure. Missing per-leg Greeks
are treated as zero so a partial chain still yields a usable aggregate.
"""

from __future__ import annotations

from backend.alpaca.models import Greeks
from backend.options.models import StrategyCandidate


def net_greeks(candidate: StrategyCandidate) -> Greeks:
    """Return position-level Greeks (per one unit of the strategy)."""
    totals = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}
    has_value = False
    for leg in candidate.legs:
        g = leg.contract.greeks
        for key in totals:
            value = getattr(g, key)
            if value is not None:
                totals[key] += leg.sign * value * leg.ratio
                has_value = True
    if not has_value:
        return Greeks()
    return Greeks(**{k: round(v, 6) for k, v in totals.items()})
