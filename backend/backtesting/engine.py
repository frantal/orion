"""Backtesting Engine.

Simulates strategy outcomes by drawing terminal underlying prices from the same
lognormal model the Quant Engine uses, then computing realized P/L per draw.
This is a *forward* Monte-Carlo simulation (historical option chains are not
available on the free feed) and is clearly labelled as such — it never claims to
predict the future.
"""

from __future__ import annotations

import numpy as np

from backend.backtesting.models import BacktestReport, StrategyBacktest
from backend.core.logging import get_logger
from backend.options.models import StrategyCandidate
from backend.portfolio.performance import compute_performance
from backend.quant.models import Opportunity
from backend.quant.probability import DEFAULT_IV, payoff_vector

logger = get_logger("backtesting.engine")


def simulate_candidate(
    candidate: StrategyCandidate,
    spot: float,
    iv: float,
    samples: int = 2000,
    seed: int | None = 7,
) -> list[float]:
    """Monte-Carlo realized P/L (dollars, per contract) for a candidate."""
    rng = np.random.default_rng(seed)
    t = max(candidate.dte, 1) / 365.0
    vol = max(iv, 1e-4) * np.sqrt(t)
    z = rng.standard_normal(samples)
    prices = spot * np.exp(-0.5 * vol**2 + vol * z)
    return [float(x) for x in payoff_vector(candidate, prices)]


class BacktestEngine:
    def run(
        self,
        opportunities: list[Opportunity],
        spot: float,
        samples: int = 2000,
        seed: int | None = 7,
    ) -> BacktestReport:
        symbol = opportunities[0].symbol if opportunities else ""
        per: list[StrategyBacktest] = []
        all_pnls: list[float] = []

        for opp in opportunities:
            iv = opp.metrics.implied_volatility or DEFAULT_IV
            pnls = simulate_candidate(opp.candidate, spot, iv, samples=samples, seed=seed)
            all_pnls.extend(pnls)
            per.append(
                StrategyBacktest(
                    opportunity_id=opp.id,
                    symbol=opp.symbol,
                    strategy=opp.strategy,
                    samples=samples,
                    implied_volatility=opp.metrics.implied_volatility,
                    analytic_expected_value=opp.metrics.expected_value,
                    performance=compute_performance(pnls),
                )
            )

        logger.info("backtest complete", extra={"symbol": symbol, "strategies": len(per)})
        return BacktestReport(
            symbol=symbol,
            per_strategy=per,
            aggregate=compute_performance(all_pnls),
        )
