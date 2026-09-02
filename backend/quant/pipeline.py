"""Opportunity pipeline — deterministic orchestration.

Ties the deterministic stages together: fetch market data and the option chain
(scoped to the strategy DTE window), classify the regime, scan for candidates,
score them with the Quant Engine, and rank by Alpha Score. This is the backbone
the Alpha Engine (Phase 4) and Decision Engine (Phase 5) build on.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from backend.alpaca.mcp_adapter import AlpacaAdapter
from backend.market.intelligence import classify_regime
from backend.market.models import MarketContext
from backend.options.scanner import ScanConfig, ScanResult, scan
from backend.quant.engine import QuantEngine, rank_opportunities
from backend.quant.models import Opportunity
from backend.core.logging import get_logger

logger = get_logger("quant.pipeline")


@dataclass
class PipelineResult:
    context: MarketContext
    scan: ScanResult
    opportunities: list[Opportunity]


async def generate_opportunities(
    adapter: AlpacaAdapter,
    symbol: str,
    config: ScanConfig | None = None,
    today: date | None = None,
) -> PipelineResult:
    """Run the deterministic opportunity pipeline for a symbol."""
    config = config or ScanConfig()
    today = today or date.today()
    symbol = symbol.upper()

    snapshot = await adapter.get_market_snapshot(symbol)
    chain = await adapter.get_option_chain(
        symbol,
        expiration_gte=today + timedelta(days=config.min_dte),
        expiration_lte=today + timedelta(days=config.max_dte),
    )

    scan_result = scan(chain, spot=snapshot.price, today=today, config=config)
    context = classify_regime(snapshot, implied_volatility=scan_result.reference_iv)

    engine = QuantEngine()
    opportunities = [
        engine.evaluate(cand, context, reference_iv=scan_result.reference_iv)
        for cand in scan_result.candidates
    ]
    opportunities = rank_opportunities(opportunities)

    logger.info(
        "pipeline complete",
        extra={
            "symbol": symbol,
            "regime": context.regime.value,
            "candidates": len(scan_result.candidates),
            "opportunities": len(opportunities),
        },
    )
    return PipelineResult(context=context, scan=scan_result, opportunities=opportunities)
