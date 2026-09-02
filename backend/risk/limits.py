"""Configurable risk limits.

Central home for every risk threshold — no magic numbers scattered through the
logic. The Risk Governor and position sizer read from :class:`RiskLimits`.
Open-interest / volume gates are opt-in because Alpaca's indicative options feed
does not always populate those fields.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskLimits:
    max_portfolio_risk: float = 0.02   # fraction of equity at risk overall
    max_single_trade_risk: float = 0.01  # fraction of equity per trade
    min_alpha_score: float = 70.0
    min_liquidity_score: float = 60.0
    max_risk_score: float = 60.0
    min_risk_reward: float = 1.5
    min_expected_value: float = 0.0  # "prove its trade": reject negative expectancy
    max_spread_percent: float = 5.0
    min_open_interest: float = 100.0
    min_volume: float = 20.0
    max_open_trades: int = 10

    # When False, missing OI/volume data is not a veto (indicative feed gaps).
    require_open_interest: bool = False
    require_volume: bool = False


def default_limits() -> RiskLimits:
    return RiskLimits()
