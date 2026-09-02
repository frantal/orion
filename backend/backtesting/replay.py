"""Replay Engine — deterministic historical-snapshot replay.

Given a strategy candidate and the actual terminal underlying prices from
historical scenarios, compute the realized P/L of each and the resulting
performance. Fully deterministic (no sampling), which makes it ideal for
regression tests and reproducible what-if analysis.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.options.models import StrategyCandidate
from backend.portfolio.performance import PerformanceStats, compute_performance


@dataclass
class ReplayScenario:
    """One historical scenario: a candidate and the observed terminal price."""

    candidate: StrategyCandidate
    terminal_price: float


def replay(candidate: StrategyCandidate, terminal_prices: list[float]) -> list[float]:
    """Realized P/L (dollars, per contract) at each terminal price."""
    return [candidate.payoff(p) for p in terminal_prices]


def replay_scenarios(scenarios: list[ReplayScenario]) -> PerformanceStats:
    """Replay a set of scenarios and return aggregate performance."""
    pnls = [s.candidate.payoff(s.terminal_price) for s in scenarios]
    return compute_performance(pnls)
