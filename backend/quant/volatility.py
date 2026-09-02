"""Volatility edge scoring.

Debit strategies (net long premium / long vega) prefer *cheap* volatility;
credit strategies (short vega) prefer *rich* volatility. The score compares the
candidate's IV to a chain reference IV and rewards the alignment.
"""

from __future__ import annotations

from backend.quant.models import clamp

EDGE_SENSITIVITY = 300.0


def volatility_score(candidate_iv: float | None, reference_iv: float | None, is_debit: bool) -> float:
    """Return a 0-100 volatility-edge score. Neutral (50) when IV is unknown."""
    if not candidate_iv or not reference_iv:
        return 50.0
    edge = (reference_iv - candidate_iv) / reference_iv  # positive => cheap vol
    signed = edge if is_debit else -edge
    return round(clamp(50.0 + signed * EDGE_SENSITIVITY), 2)
