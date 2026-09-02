"""Alpha Score, Risk Score and confidence.

Alpha Score (0-100) is a weighted blend (section 10 of the spec):
    30% expected value · 20% risk/reward · 15% liquidity ·
    15% volatility edge · 10% regime alignment · 10% catalyst/evidence

Risk Score (0-100) rises with poor liquidity and low probability of profit
(0 = low relative risk, 100 = high). All deterministic.
"""

from __future__ import annotations

from backend.market.models import MarketContext
from backend.options.models import STRATEGY_BIAS, Strategy
from backend.quant.models import clamp

# Alpha Score weights.
W_EV = 0.30
W_RR = 0.20
W_LIQ = 0.15
W_VOL = 0.15
W_REGIME = 0.10
W_CATALYST = 0.10

DEFAULT_CATALYST_SCORE = 50.0


def _ev_score(expected_value: float, max_loss: float) -> float:
    ratio = expected_value / abs(max_loss) if max_loss else 0.0
    return clamp(50.0 + ratio * 200.0)


def _rr_score(risk_reward: float) -> float:
    return clamp(risk_reward / 3.0 * 100.0)


def regime_alignment_score(strategy: Strategy, context: MarketContext) -> float:
    """Reward strategies whose directional lean matches the market bias."""
    bias = STRATEGY_BIAS.get(strategy, "neutral")
    market_bias = context.directional_bias
    if market_bias == "neutral":
        return 60.0
    return 100.0 if bias == market_bias else 20.0


def alpha_score(
    expected_value: float,
    max_loss: float,
    risk_reward: float,
    liquidity: float,
    volatility: float,
    strategy: Strategy,
    context: MarketContext,
    catalyst_score: float = DEFAULT_CATALYST_SCORE,
) -> float:
    score = (
        W_EV * _ev_score(expected_value, max_loss)
        + W_RR * _rr_score(risk_reward)
        + W_LIQ * liquidity
        + W_VOL * volatility
        + W_REGIME * regime_alignment_score(strategy, context)
        + W_CATALYST * catalyst_score
    )
    return round(clamp(score), 2)


def risk_score(liquidity: float, probability_of_profit: float) -> float:
    score = 0.5 * (100.0 - liquidity) + 0.5 * (100.0 - probability_of_profit * 100.0)
    return round(clamp(score), 2)


def confidence(probability_of_profit: float, liquidity: float) -> float:
    score = 40.0 + probability_of_profit * 50.0 + (liquidity - 50.0) * 0.2
    return round(clamp(score), 2)
