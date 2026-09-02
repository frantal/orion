"""Builders that turn option contracts into :class:`StrategyCandidate` objects.

Each builder computes entry economics (net premium, max profit/loss, breakeven)
deterministically. A builder returns ``None`` when required prices are missing or
the economics are degenerate — no LLM is involved.
"""

from __future__ import annotations

from datetime import date

from backend.alpaca.models import OptionContract, OptionType
from backend.options.models import Action, OptionLeg, Strategy, StrategyCandidate

CONTRACT_MULTIPLIER = 100


def _mid(contract: OptionContract) -> float | None:
    m = contract.mid
    return m if m and m > 0 else None


def build_long(contract: OptionContract, dte: int) -> StrategyCandidate | None:
    """Long Call or Long Put."""
    mid = _mid(contract)
    if mid is None:
        return None
    is_call = contract.option_type is OptionType.CALL
    strategy = Strategy.LONG_CALL if is_call else Strategy.LONG_PUT
    breakeven = contract.strike + mid if is_call else contract.strike - mid
    return StrategyCandidate(
        symbol=contract.underlying,
        strategy=strategy,
        legs=[OptionLeg(contract=contract, action=Action.BUY)],
        expiration=contract.expiration,
        dte=dte,
        net_premium=mid,
        entry_price=round(mid * CONTRACT_MULTIPLIER, 2),
        max_profit=None,  # unbounded
        max_loss=round(mid * CONTRACT_MULTIPLIER, 2),
        breakevens=[round(breakeven, 4)],
        width=None,
    )


def _vertical(
    strategy: Strategy,
    long_contract: OptionContract,
    short_contract: OptionContract,
    dte: int,
    expiration: date,
) -> StrategyCandidate | None:
    long_mid = _mid(long_contract)
    short_mid = _mid(short_contract)
    if long_mid is None or short_mid is None:
        return None

    net_premium = long_mid - short_mid  # + = debit, - = credit
    width = abs(short_contract.strike - long_contract.strike)
    if width <= 0:
        return None

    is_debit = net_premium > 0
    if is_debit:
        debit = net_premium
        if debit >= width:  # no edge — pay more than the spread is worth
            return None
        max_loss = round(debit * CONTRACT_MULTIPLIER, 2)
        max_profit = round((width - debit) * CONTRACT_MULTIPLIER, 2)
    else:
        credit = -net_premium
        if credit >= width:
            return None
        max_profit = round(credit * CONTRACT_MULTIPLIER, 2)
        max_loss = round((width - credit) * CONTRACT_MULTIPLIER, 2)

    breakeven = _breakeven(strategy, long_contract, short_contract, net_premium)
    legs = [
        OptionLeg(contract=long_contract, action=Action.BUY),
        OptionLeg(contract=short_contract, action=Action.SELL),
    ]
    return StrategyCandidate(
        symbol=long_contract.underlying,
        strategy=strategy,
        legs=legs,
        expiration=expiration,
        dte=dte,
        net_premium=round(net_premium, 4),
        entry_price=round(abs(net_premium) * CONTRACT_MULTIPLIER, 2),
        max_profit=max_profit,
        max_loss=max_loss,
        breakevens=[round(breakeven, 4)],
        width=width,
    )


def _breakeven(
    strategy: Strategy,
    long_c: OptionContract,
    short_c: OptionContract,
    net_premium: float,
) -> float:
    debit = net_premium
    credit = -net_premium
    if strategy is Strategy.BULL_CALL_SPREAD:
        return long_c.strike + debit
    if strategy is Strategy.BEAR_PUT_SPREAD:
        return long_c.strike - debit
    if strategy is Strategy.BULL_PUT_SPREAD:
        return short_c.strike - credit
    if strategy is Strategy.BEAR_CALL_SPREAD:
        return short_c.strike + credit
    raise ValueError(f"Not a vertical strategy: {strategy}")


def build_bull_call_spread(lower: OptionContract, higher: OptionContract, dte: int) -> StrategyCandidate | None:
    """Buy lower-strike call, sell higher-strike call (debit)."""
    return _vertical(Strategy.BULL_CALL_SPREAD, lower, higher, dte, lower.expiration)


def build_bear_call_spread(lower: OptionContract, higher: OptionContract, dte: int) -> StrategyCandidate | None:
    """Sell lower-strike call, buy higher-strike call (credit). Long leg = higher."""
    return _vertical(Strategy.BEAR_CALL_SPREAD, higher, lower, dte, lower.expiration)


def build_bull_put_spread(lower: OptionContract, higher: OptionContract, dte: int) -> StrategyCandidate | None:
    """Sell higher-strike put, buy lower-strike put (credit). Long leg = lower."""
    return _vertical(Strategy.BULL_PUT_SPREAD, lower, higher, dte, lower.expiration)


def build_bear_put_spread(lower: OptionContract, higher: OptionContract, dte: int) -> StrategyCandidate | None:
    """Buy higher-strike put, sell lower-strike put (debit). Long leg = higher."""
    return _vertical(Strategy.BEAR_PUT_SPREAD, higher, lower, dte, lower.expiration)
