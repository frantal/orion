"""Liquidity scoring for a strategy candidate.

Aggregates each leg's spread, volume and open interest into a 0-100 score. The
weakest leg dominates (a chain is only as liquid as its worst leg). Unknown
open interest is treated as neutral because Alpaca's indicative options feed
does not always populate it.
"""

from __future__ import annotations

from backend.alpaca.models import OptionContract
from backend.options.models import StrategyCandidate
from backend.quant.models import clamp

VOLUME_TARGET = 200.0
OI_TARGET = 500.0


def _leg_liquidity(contract: OptionContract) -> float:
    sp = contract.spread_percent
    s_spread = clamp(100.0 - sp * 10.0) if sp is not None else 0.0

    vol = contract.volume
    s_volume = clamp(min(vol, VOLUME_TARGET) / VOLUME_TARGET * 100.0) if vol is not None else 30.0

    oi = contract.open_interest
    s_oi = clamp(min(oi, OI_TARGET) / OI_TARGET * 100.0) if oi is not None else 50.0

    return 0.5 * s_spread + 0.25 * s_volume + 0.25 * s_oi


def liquidity_score(candidate: StrategyCandidate) -> float:
    """Return a 0-100 liquidity score (weakest leg dominates)."""
    scores = [_leg_liquidity(leg.contract) for leg in candidate.legs]
    return round(min(scores), 2) if scores else 0.0
