"""Tests for the Quant Engine (probability, expected value, scoring integration)."""

from __future__ import annotations

import numpy as np
import pytest

from backend.alpaca.models import OptionType, StockSnapshot
from backend.market.intelligence import classify_regime
from backend.options.spreads import build_bull_call_spread, build_long
from backend.quant import expected_value
from backend.quant.engine import QuantEngine, rank_opportunities
from backend.quant.probability import payoff_vector, terminal_distribution
from tests.conftest import make_contract


def _context(price: float = 100.0, iv: float | None = 0.20):
    snap = StockSnapshot(symbol="SPY", price=price, prev_close=price)
    return classify_regime(snap, implied_volatility=iv)


def test_terminal_distribution_normalized() -> None:
    prices, weights = terminal_distribution(spot=100, iv=0.2, dte_days=30)
    assert prices.shape == weights.shape
    assert weights.sum() == pytest.approx(1.0, abs=1e-9)
    # Expected terminal price ~ spot (zero drift, small vol adjustment).
    assert float((prices * weights).sum()) == pytest.approx(100.0, rel=0.02)


def test_payoff_vector_matches_scalar() -> None:
    lower = make_contract(100, OptionType.CALL, bid=2.9, ask=3.1)
    higher = make_contract(105, OptionType.CALL, bid=1.1, ask=1.3)
    cand = build_bull_call_spread(lower, higher, dte=30)
    assert cand is not None
    prices = np.array([90.0, 110.0])
    pv = payoff_vector(cand, prices)
    assert pv[0] == pytest.approx(cand.payoff(90.0))
    assert pv[1] == pytest.approx(cand.payoff(110.0))


def test_expected_value_pop_bounds() -> None:
    lower = make_contract(100, OptionType.CALL, bid=2.9, ask=3.1)
    higher = make_contract(105, OptionType.CALL, bid=1.1, ask=1.3)
    cand = build_bull_call_spread(lower, higher, dte=30)
    assert cand is not None
    ev = expected_value.evaluate(cand, spot=100.0, iv=0.2)
    assert 0.0 <= ev.probability_of_profit <= 1.0
    assert ev.avg_win > 0
    assert ev.avg_loss < 0


def test_engine_produces_scored_opportunity() -> None:
    lower = make_contract(100, OptionType.CALL, bid=2.9, ask=3.1)
    higher = make_contract(105, OptionType.CALL, bid=1.1, ask=1.3)
    cand = build_bull_call_spread(lower, higher, dte=30)
    assert cand is not None
    opp = QuantEngine().evaluate(cand, _context(), reference_iv=0.20)
    assert 0 <= opp.metrics.alpha_score <= 100
    assert 0 <= opp.metrics.risk_score <= 100
    assert opp.metrics.risk_reward == pytest.approx(320.0 / 180.0, rel=1e-3)
    assert opp.invalidation_conditions  # non-empty


def test_rank_orders_by_alpha() -> None:
    ctx = _context()
    engine = QuantEngine()
    a = engine.evaluate(
        build_bull_call_spread(
            make_contract(100, OptionType.CALL, bid=2.9, ask=3.1),
            make_contract(105, OptionType.CALL, bid=1.1, ask=1.3),
            dte=30,
        ),
        ctx,
        reference_iv=0.20,
    )
    b = engine.evaluate(
        build_long(make_contract(100, OptionType.CALL, bid=2.9, ask=3.1), dte=30),
        ctx,
        reference_iv=0.20,
    )
    ranked = rank_opportunities([b, a])
    assert ranked[0].metrics.alpha_score >= ranked[1].metrics.alpha_score
