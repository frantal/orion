"""Tests for options strategy builders and the scanner."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from backend.alpaca.models import OptionChain, OptionType
from backend.options.models import Action, Strategy
from backend.options.scanner import ScanConfig, scan
from backend.options.spreads import (
    build_bear_call_spread,
    build_bull_call_spread,
    build_bull_put_spread,
    build_long,
)
from tests.conftest import make_contract


def test_long_call_economics() -> None:
    c = make_contract(100, OptionType.CALL, bid=2.90, ask=3.10)
    cand = build_long(c, dte=30)
    assert cand is not None
    assert cand.strategy is Strategy.LONG_CALL
    assert cand.max_loss == 300.0
    assert cand.max_profit is None
    assert cand.breakevens[0] == pytest.approx(103.0)
    assert cand.is_debit is True


def test_bull_call_spread_economics() -> None:
    lower = make_contract(100, OptionType.CALL, bid=2.90, ask=3.10)   # mid 3.00
    higher = make_contract(105, OptionType.CALL, bid=1.10, ask=1.30)  # mid 1.20
    cand = build_bull_call_spread(lower, higher, dte=30)
    assert cand is not None
    assert cand.strategy is Strategy.BULL_CALL_SPREAD
    assert cand.max_loss == pytest.approx(180.0)
    assert cand.max_profit == pytest.approx(320.0)
    assert cand.breakevens[0] == pytest.approx(101.80)
    # legs: buy lower, sell higher
    assert cand.legs[0].action is Action.BUY
    assert cand.legs[0].contract.strike == 100
    assert cand.legs[1].action is Action.SELL


def test_bull_put_spread_is_credit() -> None:
    lower = make_contract(95, OptionType.PUT, bid=0.90, ask=1.10)   # mid 1.00
    higher = make_contract(100, OptionType.PUT, bid=2.40, ask=2.60)  # mid 2.50
    cand = build_bull_put_spread(lower, higher, dte=30)
    assert cand is not None
    assert cand.strategy is Strategy.BULL_PUT_SPREAD
    assert cand.is_debit is False  # credit received
    # credit = 2.50 - 1.00 = 1.50, width 5 -> max_profit 150, max_loss 350
    assert cand.max_profit == pytest.approx(150.0)
    assert cand.max_loss == pytest.approx(350.0)
    assert cand.breakevens[0] == pytest.approx(98.5)


def test_spread_rejected_when_no_edge() -> None:
    # Debit equals width -> no edge, builder returns None.
    lower = make_contract(100, OptionType.CALL, bid=4.9, ask=5.1)  # mid 5.0
    higher = make_contract(105, OptionType.CALL, bid=0.0, ask=0.0)  # no mid
    assert build_bull_call_spread(lower, higher, dte=30) is None


def test_payoff_at_expiration() -> None:
    lower = make_contract(100, OptionType.CALL, bid=2.90, ask=3.10)
    higher = make_contract(105, OptionType.CALL, bid=1.10, ask=1.30)
    cand = build_bull_call_spread(lower, higher, dte=30)
    assert cand is not None
    assert cand.payoff(90) == pytest.approx(-180.0)   # both expire worthless
    assert cand.payoff(110) == pytest.approx(320.0)   # max profit above 105


def test_scanner_generates_candidates() -> None:
    exp = date.today() + timedelta(days=30)
    contracts = []
    for strike in range(90, 111, 5):
        contracts.append(
            make_contract(strike, OptionType.CALL, bid=max(0.2, (110 - strike) * 0.1),
                          ask=max(0.3, (110 - strike) * 0.1 + 0.1), dte=30)
        )
        contracts.append(
            make_contract(strike, OptionType.PUT, bid=max(0.2, (strike - 90) * 0.1),
                          ask=max(0.3, (strike - 90) * 0.1 + 0.1), dte=30)
        )
    chain = OptionChain(underlying="SPY", contracts=contracts)
    result = scan(chain, spot=100.0, config=ScanConfig(max_candidates=50))
    assert result.expiration == exp
    assert len(result.candidates) > 0
    strategies = {c.strategy for c in result.candidates}
    assert Strategy.BULL_CALL_SPREAD in strategies


def test_scanner_no_expiration_when_out_of_window() -> None:
    contracts = [make_contract(100, OptionType.CALL, bid=1.0, ask=1.1, dte=120)]
    chain = OptionChain(underlying="SPY", contracts=contracts)
    result = scan(chain, spot=100.0)
    assert result.expiration is None
    assert result.candidates == []
