"""Options Scanner.

Filters an option chain for tradability (valid prices, acceptable spread) and
generates a bounded set of :class:`StrategyCandidate` objects around the money.
All logic is deterministic; the goal is to hand the Quant Engine a small, clean
candidate set (RAW DATA -> FILTER -> QUANT -> TOP CANDIDATES -> LLM).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date

from backend.alpaca.models import OptionChain, OptionContract, OptionType
from backend.core.logging import get_logger
from backend.options.models import StrategyCandidate
from backend.options.spreads import (
    build_bear_call_spread,
    build_bear_put_spread,
    build_bull_call_spread,
    build_bull_put_spread,
    build_long,
)

logger = get_logger("options.scanner")


@dataclass
class ScanConfig:
    """Bounds and filters for the scan (kept explicit — no magic numbers)."""

    min_dte: int = 7
    max_dte: int = 60
    target_dte: int = 30
    strikes_each_side: int = 6
    max_widths: int = 3
    scan_max_spread_pct: float = 25.0
    max_candidates: int = 80
    include_singles: bool = True


@dataclass
class ScanResult:
    underlying: str
    spot: float
    expiration: date | None
    candidates: list[StrategyCandidate] = field(default_factory=list)
    reference_iv: float | None = None
    contracts_considered: int = 0


def _is_tradable(contract: OptionContract, max_spread_pct: float) -> bool:
    if contract.mid is None or contract.mid <= 0:
        return False
    sp = contract.spread_percent
    if sp is not None and sp > max_spread_pct:
        return False
    return True


def _reference_iv(contracts: list[OptionContract]) -> float | None:
    ivs = [c.implied_volatility for c in contracts if c.implied_volatility]
    return round(statistics.median(ivs), 4) if ivs else None


def _select_expiration(chain: OptionChain, today: date, config: ScanConfig) -> date | None:
    candidates: list[tuple[int, date]] = []
    for exp in chain.expirations():
        dte = (exp - today).days
        if config.min_dte <= dte <= config.max_dte:
            candidates.append((abs(dte - config.target_dte), exp))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][1]


def _near_money(contracts: list[OptionContract], spot: float, n: int) -> list[OptionContract]:
    ordered = sorted(contracts, key=lambda c: c.strike)
    if not ordered:
        return []
    atm_index = min(range(len(ordered)), key=lambda i: abs(ordered[i].strike - spot))
    lo = max(0, atm_index - n)
    hi = min(len(ordered), atm_index + n + 1)
    return ordered[lo:hi]


def scan(chain: OptionChain, spot: float, today: date | None = None, config: ScanConfig | None = None) -> ScanResult:
    """Produce a bounded set of strategy candidates from a chain."""
    today = today or date.today()
    config = config or ScanConfig()

    tradable = [c for c in chain.contracts if _is_tradable(c, config.scan_max_spread_pct)]
    reference_iv = _reference_iv(tradable)
    expiration = _select_expiration(
        OptionChain(underlying=chain.underlying, contracts=tradable), today, config
    )
    result = ScanResult(
        underlying=chain.underlying,
        spot=spot,
        expiration=expiration,
        reference_iv=reference_iv,
        contracts_considered=len(tradable),
    )
    if expiration is None:
        logger.info("no suitable expiration", extra={"underlying": chain.underlying})
        return result

    dte = (expiration - today).days
    exp_contracts = [c for c in tradable if c.expiration == expiration]
    calls = _near_money([c for c in exp_contracts if c.option_type is OptionType.CALL], spot, config.strikes_each_side)
    puts = _near_money([c for c in exp_contracts if c.option_type is OptionType.PUT], spot, config.strikes_each_side)

    candidates: list[StrategyCandidate] = []

    if config.include_singles:
        for c in calls + puts:
            built = build_long(c, dte)
            if built is not None:
                candidates.append(built)

    candidates.extend(_verticals(calls, config, dte, is_call=True))
    candidates.extend(_verticals(puts, config, dte, is_call=False))

    candidates = candidates[: config.max_candidates]
    result.candidates = candidates
    logger.info(
        "scan complete",
        extra={
            "underlying": chain.underlying,
            "expiration": expiration.isoformat(),
            "candidates": len(candidates),
        },
    )
    return result


def _verticals(contracts: list[OptionContract], config: ScanConfig, dte: int, is_call: bool) -> list[StrategyCandidate]:
    ordered = sorted(contracts, key=lambda c: c.strike)
    out: list[StrategyCandidate] = []
    for i in range(len(ordered)):
        for w in range(1, config.max_widths + 1):
            j = i + w
            if j >= len(ordered):
                break
            lower, higher = ordered[i], ordered[j]
            if is_call:
                for built in (build_bull_call_spread(lower, higher, dte), build_bear_call_spread(lower, higher, dte)):
                    if built is not None:
                        out.append(built)
            else:
                for built in (build_bull_put_spread(lower, higher, dte), build_bear_put_spread(lower, higher, dte)):
                    if built is not None:
                        out.append(built)
    return out
