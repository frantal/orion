"""Market Intelligence — deterministic market regime classification.

No LLM is used here. The regime is derived from price action and (optionally)
implied volatility. This feeds the Alpha Score's regime-alignment component and
the dashboard.
"""

from __future__ import annotations

from backend.alpaca.models import StockSnapshot
from backend.market.models import MarketContext, MarketRegime
from backend.core.logging import get_logger

logger = get_logger("market.intelligence")

# Thresholds (kept explicit rather than magic numbers scattered in logic).
BULLISH_CHANGE_PCT = 0.4
BEARISH_CHANGE_PCT = -0.4
HIGH_IV = 0.35
LOW_IV = 0.15
WIDE_RANGE_PCT = 2.5


def classify_regime(
    snapshot: StockSnapshot, implied_volatility: float | None = None
) -> MarketContext:
    """Classify the market regime for a symbol from a snapshot.

    Directional bias comes from the day's change; the headline regime also
    accounts for volatility (IV when available, otherwise intraday range).
    """
    change_pct = snapshot.change_percent
    notes: list[str] = []

    # Directional bias.
    if change_pct is None:
        bias = "neutral"
    elif change_pct >= BULLISH_CHANGE_PCT:
        bias = "bullish"
    elif change_pct <= BEARISH_CHANGE_PCT:
        bias = "bearish"
    else:
        bias = "neutral"

    # Intraday range as a volatility proxy when IV is absent.
    day_range_pct: float | None = None
    if snapshot.day_high and snapshot.day_low and snapshot.price:
        day_range_pct = round((snapshot.day_high - snapshot.day_low) / snapshot.price * 100, 4)

    # Volatility read.
    high_vol = False
    low_vol = False
    if implied_volatility is not None:
        high_vol = implied_volatility >= HIGH_IV
        low_vol = implied_volatility <= LOW_IV
        notes.append(f"IV={implied_volatility:.2%}")
    elif day_range_pct is not None:
        high_vol = day_range_pct >= WIDE_RANGE_PCT
        notes.append(f"day_range={day_range_pct:.2f}%")

    # Headline regime: volatility dominates when extreme, else direction.
    if high_vol:
        regime = MarketRegime.HIGH_VOLATILITY
    elif bias == "bullish":
        regime = MarketRegime.BULLISH
    elif bias == "bearish":
        regime = MarketRegime.BEARISH
    elif low_vol:
        regime = MarketRegime.LOW_VOLATILITY
    else:
        regime = MarketRegime.NEUTRAL

    context = MarketContext(
        symbol=snapshot.symbol,
        price=snapshot.price,
        regime=regime,
        directional_bias=bias,
        change_percent=change_pct,
        implied_volatility=implied_volatility,
        day_range_percent=day_range_pct,
        notes=notes,
    )
    logger.info(
        "regime classified",
        extra={"symbol": snapshot.symbol, "regime": regime.value, "bias": bias},
    )
    return context
