"""Options strategy models.

A :class:`StrategyCandidate` is a proposed trade (one or two legs) with its
entry economics computed. The terminal :meth:`StrategyCandidate.payoff` is
strategy-agnostic — it sums leg intrinsic values minus the net premium — so the
Quant Engine can evaluate any strategy through one code path.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

from backend.alpaca.models import OptionContract, OptionType

CONTRACT_MULTIPLIER = 100


class Strategy(str, Enum):
    LONG_CALL = "Long Call"
    LONG_PUT = "Long Put"
    BULL_CALL_SPREAD = "Bull Call Spread"
    BEAR_PUT_SPREAD = "Bear Put Spread"
    BULL_PUT_SPREAD = "Bull Put Spread"
    BEAR_CALL_SPREAD = "Bear Call Spread"


class Action(str, Enum):
    BUY = "buy"
    SELL = "sell"


# Directional lean of each strategy, used for regime alignment scoring.
STRATEGY_BIAS: dict[Strategy, str] = {
    Strategy.LONG_CALL: "bullish",
    Strategy.BULL_CALL_SPREAD: "bullish",
    Strategy.BULL_PUT_SPREAD: "bullish",
    Strategy.LONG_PUT: "bearish",
    Strategy.BEAR_PUT_SPREAD: "bearish",
    Strategy.BEAR_CALL_SPREAD: "bearish",
}


class OptionLeg(BaseModel):
    contract: OptionContract
    action: Action
    ratio: int = 1

    @property
    def sign(self) -> int:
        return 1 if self.action is Action.BUY else -1


class StrategyCandidate(BaseModel):
    """A proposed options strategy with computed entry economics."""

    symbol: str
    strategy: Strategy
    legs: list[OptionLeg]
    expiration: date
    dte: int

    # Signed net premium per share: positive = debit paid, negative = credit received.
    net_premium: float
    # Absolute cash to enter one unit (display), = abs(net_premium) * multiplier.
    entry_price: float
    max_profit: float | None  # None = theoretically unlimited (long options)
    max_loss: float
    breakevens: list[float] = Field(default_factory=list)
    width: float | None = None

    @property
    def is_debit(self) -> bool:
        return self.net_premium > 0

    @property
    def cost_basis(self) -> float:
        """Signed dollar cost at entry (debit positive, credit negative)."""
        return self.net_premium * CONTRACT_MULTIPLIER

    def payoff(self, underlying_price: float) -> float:
        """Profit/loss in dollars at expiration for one unit at ``underlying_price``."""
        terminal = 0.0
        for leg in self.legs:
            c = leg.contract
            if c.option_type is OptionType.CALL:
                intrinsic = max(underlying_price - c.strike, 0.0)
            else:
                intrinsic = max(c.strike - underlying_price, 0.0)
            terminal += leg.sign * CONTRACT_MULTIPLIER * intrinsic * leg.ratio
        return terminal - self.cost_basis

    def representative_iv(self) -> float | None:
        ivs = [leg.contract.implied_volatility for leg in self.legs if leg.contract.implied_volatility]
        return max(ivs) if ivs else None

    def worst_spread_percent(self) -> float | None:
        spreads = [leg.contract.spread_percent for leg in self.legs if leg.contract.spread_percent is not None]
        return max(spreads) if spreads else None

    def min_volume(self) -> float | None:
        vols = [leg.contract.volume for leg in self.legs if leg.contract.volume is not None]
        return min(vols) if vols else None

    def min_open_interest(self) -> float | None:
        ois = [leg.contract.open_interest for leg in self.legs if leg.contract.open_interest is not None]
        return min(ois) if ois else None
