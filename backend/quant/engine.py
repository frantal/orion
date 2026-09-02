"""Quant Engine orchestration.

Turns a :class:`StrategyCandidate` into a fully scored :class:`Opportunity`.
This is deterministic intelligence: pricing, probability, EV, scoring — all in
Python, none delegated to an LLM.
"""

from __future__ import annotations

from backend.market.models import MarketContext
from backend.options.models import Strategy, StrategyCandidate
from backend.quant import expected_value, liquidity, scoring, volatility
from backend.quant.models import Opportunity, QuantMetrics, clamp
from backend.quant.probability import DEFAULT_IV
from backend.core.logging import get_logger

logger = get_logger("quant.engine")


class QuantEngine:
    """Deterministic quantitative analysis of option strategy candidates."""

    def evaluate(
        self,
        candidate: StrategyCandidate,
        context: MarketContext,
        reference_iv: float | None = None,
        catalyst_score: float = scoring.DEFAULT_CATALYST_SCORE,
    ) -> Opportunity:
        spot = context.price
        iv = candidate.representative_iv() or reference_iv or DEFAULT_IV

        ev = expected_value.evaluate(candidate, spot, iv)
        liq = liquidity.liquidity_score(candidate)
        vol = volatility.volatility_score(iv, reference_iv, candidate.is_debit)
        rr = self._risk_reward(candidate, ev.avg_win, ev.avg_loss)

        alpha = scoring.alpha_score(
            expected_value=ev.expected_value,
            max_loss=candidate.max_loss,
            risk_reward=rr,
            liquidity=liq,
            volatility=vol,
            strategy=candidate.strategy,
            context=context,
            catalyst_score=catalyst_score,
        )
        risk = scoring.risk_score(liq, ev.probability_of_profit)
        conf = scoring.confidence(ev.probability_of_profit, liq)

        metrics = QuantMetrics(
            probability_of_profit=ev.probability_of_profit,
            expected_value=ev.expected_value,
            risk_reward=round(rr, 4),
            avg_win=ev.avg_win,
            avg_loss=ev.avg_loss,
            liquidity_score=liq,
            volatility_score=vol,
            implied_volatility=round(iv, 4) if iv else None,
            alpha_score=alpha,
            risk_score=risk,
            confidence=conf,
        )
        return Opportunity(
            symbol=candidate.symbol,
            candidate=candidate,
            metrics=metrics,
            market_regime=context.regime,
            catalysts=[],
            invalidation_conditions=self._invalidation(candidate),
        )

    @staticmethod
    def _risk_reward(candidate: StrategyCandidate, avg_win: float, avg_loss: float) -> float:
        """Defined-risk: max_profit/max_loss. Unbounded: distribution avg_win/avg_loss."""
        if candidate.max_profit is not None and candidate.max_loss > 0:
            return round(candidate.max_profit / candidate.max_loss, 4)
        if avg_loss < 0:
            return round(avg_win / abs(avg_loss), 4)
        return 0.0

    @staticmethod
    def _invalidation(candidate: StrategyCandidate) -> list[str]:
        notes: list[str] = []
        for be in candidate.breakevens:
            notes.append(f"Underlying closes through breakeven {be:.2f} at expiration")
        if candidate.is_debit:
            notes.append("Implied volatility contraction (long premium decays)")
        else:
            notes.append("Implied volatility expansion / adverse gap through short strike")
        notes.append(f"Time decay against thesis within {candidate.dte} DTE")
        return notes


def rank_opportunities(opportunities: list[Opportunity]) -> list[Opportunity]:
    """Sort opportunities by Alpha Score descending."""
    return sorted(opportunities, key=lambda o: o.metrics.alpha_score, reverse=True)
