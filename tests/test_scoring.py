"""Tests for scoring components: liquidity, volatility edge, alpha/risk scores."""

from __future__ import annotations

import pytest

from backend.alpaca.models import OptionType, StockSnapshot
from backend.market.intelligence import classify_regime
from backend.options.models import Strategy
from backend.options.spreads import build_bull_call_spread
from backend.quant import scoring, volatility
from backend.quant.liquidity import liquidity_score
from tests.conftest import make_contract


def _context(change_pct: float = 0.0):
    price = 100.0
    prev = price / (1 + change_pct / 100)
    snap = StockSnapshot(symbol="SPY", price=price, prev_close=prev)
    return classify_regime(snap, implied_volatility=0.20)


def test_liquidity_high_for_tight_liquid_legs() -> None:
    lower = make_contract(100, OptionType.CALL, bid=2.98, ask=3.02, volume=200, open_interest=500)
    higher = make_contract(105, OptionType.CALL, bid=1.18, ask=1.22, volume=200, open_interest=500)
    cand = build_bull_call_spread(lower, higher, dte=30)
    assert cand is not None
    assert liquidity_score(cand) > 80


def test_liquidity_low_for_wide_spread() -> None:
    lower = make_contract(100, OptionType.CALL, bid=2.0, ask=4.0, volume=5, open_interest=None)
    higher = make_contract(105, OptionType.CALL, bid=0.5, ask=1.9, volume=5, open_interest=None)
    cand = build_bull_call_spread(lower, higher, dte=30)
    assert cand is not None
    assert liquidity_score(cand) < 40


def test_volatility_score_debit_prefers_cheap_vol() -> None:
    cheap = volatility.volatility_score(candidate_iv=0.15, reference_iv=0.25, is_debit=True)
    rich = volatility.volatility_score(candidate_iv=0.35, reference_iv=0.25, is_debit=True)
    assert cheap > 50 > rich


def test_volatility_score_credit_prefers_rich_vol() -> None:
    rich = volatility.volatility_score(candidate_iv=0.35, reference_iv=0.25, is_debit=False)
    cheap = volatility.volatility_score(candidate_iv=0.15, reference_iv=0.25, is_debit=False)
    assert rich > 50 > cheap


def test_volatility_score_neutral_when_unknown() -> None:
    assert volatility.volatility_score(None, 0.25, True) == 50.0


def test_regime_alignment_rewards_matching_bias() -> None:
    bullish_ctx = _context(change_pct=1.0)  # bullish
    aligned = scoring.regime_alignment_score(Strategy.BULL_CALL_SPREAD, bullish_ctx)
    counter = scoring.regime_alignment_score(Strategy.BEAR_PUT_SPREAD, bullish_ctx)
    assert aligned == 100.0
    assert counter == 20.0


def test_alpha_score_in_range() -> None:
    ctx = _context(change_pct=1.0)
    score = scoring.alpha_score(
        expected_value=20.0,
        max_loss=180.0,
        risk_reward=1.75,
        liquidity=90.0,
        volatility=70.0,
        strategy=Strategy.BULL_CALL_SPREAD,
        context=ctx,
    )
    assert 0 <= score <= 100
    assert score > 50


def test_risk_score_rises_with_poor_liquidity_and_low_pop() -> None:
    good = scoring.risk_score(liquidity=90.0, probability_of_profit=0.7)
    bad = scoring.risk_score(liquidity=20.0, probability_of_profit=0.2)
    assert bad > good
