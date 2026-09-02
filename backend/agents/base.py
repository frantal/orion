"""Base agent interface and prompt-context helpers.

:class:`TradingAgent` is the extensible interface (section 34) that future
agents (income, volatility, hedging, …) can implement. Only structured,
ORION-computed data is exposed to the generative layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.quant.models import Opportunity


class TradingAgent(ABC):
    """Extensible base for ORION trading agents."""

    name: str = "agent"

    @abstractmethod
    async def analyze(self, opportunity: Opportunity) -> Any:
        """Produce this agent's assessment of an opportunity."""

    def explain(self, opportunity: Opportunity) -> str:
        """Human-readable one-line summary of the opportunity."""
        m = opportunity.metrics
        return (
            f"{opportunity.symbol} {opportunity.strategy} — "
            f"alpha {m.alpha_score:.0f}, risk {m.risk_score:.0f}, "
            f"EV ${m.expected_value:.2f}, POP {m.probability_of_profit:.0%}"
        )


def opportunity_summary(opportunity: Opportunity) -> dict[str, Any]:
    """Compact, LLM-safe structured summary of an opportunity (no raw text)."""
    cand = opportunity.candidate
    m = opportunity.metrics
    return {
        "symbol": opportunity.symbol,
        "strategy": opportunity.strategy,
        "market_regime": opportunity.market_regime.value,
        "expiration": cand.expiration.isoformat(),
        "days_to_expiration": cand.dte,
        "legs": [
            {
                "action": leg.action.value,
                "type": leg.contract.option_type.value,
                "strike": leg.contract.strike,
            }
            for leg in cand.legs
        ],
        "entry_price": cand.entry_price,
        "max_profit": cand.max_profit,
        "max_loss": cand.max_loss,
        "breakevens": cand.breakevens,
        "expected_value": m.expected_value,
        "probability_of_profit": m.probability_of_profit,
        "risk_reward": m.risk_reward,
        "alpha_score": m.alpha_score,
        "risk_score": m.risk_score,
        "liquidity_score": m.liquidity_score,
        "volatility_score": m.volatility_score,
        "implied_volatility": m.implied_volatility,
        "invalidation_conditions": opportunity.invalidation_conditions,
    }
