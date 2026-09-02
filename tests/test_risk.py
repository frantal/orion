"""Tests for the Risk Governor and position sizing."""

from __future__ import annotations

import pytest

from backend.alpaca.models import OptionType
from backend.market.models import MarketRegime
from backend.options.spreads import build_bull_call_spread
from backend.quant.models import Opportunity, QuantMetrics
from backend.risk.governor import RiskGovernor
from backend.risk.limits import RiskLimits
from backend.risk.models import RiskStatus
from backend.risk.position_sizing import size_position
from tests.conftest import make_contract


def _candidate(bid_low=2.96, ask_low=3.04, bid_high=1.18, ask_high=1.22):
    lower = make_contract(100, OptionType.CALL, bid=bid_low, ask=ask_low)
    higher = make_contract(105, OptionType.CALL, bid=bid_high, ask=ask_high)
    cand = build_bull_call_spread(lower, higher, dte=30)
    assert cand is not None
    return cand


def _opportunity(
    *,
    alpha=85.0,
    risk=25.0,
    liquidity=90.0,
    risk_reward=1.75,
    pop=0.6,
    candidate=None,
) -> Opportunity:
    candidate = candidate or _candidate()
    metrics = QuantMetrics(
        probability_of_profit=pop,
        expected_value=20.0,
        risk_reward=risk_reward,
        avg_win=200.0,
        avg_loss=-150.0,
        liquidity_score=liquidity,
        volatility_score=70.0,
        implied_volatility=0.2,
        alpha_score=alpha,
        risk_score=risk,
        confidence=70.0,
    )
    return Opportunity(
        symbol="SPY",
        candidate=candidate,
        metrics=metrics,
        market_regime=MarketRegime.BULLISH,
    )


# --- Position sizing ---

def test_position_sizing_basic() -> None:
    sizing = size_position(account_equity=100_000, max_loss_per_contract=180.0)
    assert sizing.executable is True
    assert sizing.contracts == 5  # floor(1000 / 180)
    assert sizing.total_max_loss == pytest.approx(900.0)


def test_position_sizing_insufficient_budget() -> None:
    sizing = size_position(account_equity=100_000, max_loss_per_contract=1500.0)
    assert sizing.executable is False
    assert sizing.contracts == 0


def test_position_sizing_non_positive_loss() -> None:
    sizing = size_position(account_equity=100_000, max_loss_per_contract=0.0)
    assert sizing.executable is False


# --- Risk Governor ---

def test_governor_pass_on_good_opportunity() -> None:
    verdict = RiskGovernor().evaluate(_opportunity(), account_equity=100_000)
    assert verdict.status is RiskStatus.PASS
    assert verdict.is_pass
    assert verdict.sizing is not None and verdict.sizing.executable


def test_governor_veto_low_alpha() -> None:
    verdict = RiskGovernor().evaluate(_opportunity(alpha=50.0), account_equity=100_000)
    assert verdict.status is RiskStatus.VETO
    assert any("Alpha" in r for r in verdict.reasons)


def test_governor_veto_low_liquidity() -> None:
    verdict = RiskGovernor().evaluate(_opportunity(liquidity=30.0), account_equity=100_000)
    assert verdict.status is RiskStatus.VETO
    assert any("Liquidity" in r for r in verdict.reasons)


def test_governor_veto_low_risk_reward() -> None:
    verdict = RiskGovernor().evaluate(_opportunity(risk_reward=1.0), account_equity=100_000)
    assert verdict.status is RiskStatus.VETO
    assert any("Risk/Reward" in r for r in verdict.reasons)


def test_governor_veto_high_risk_score() -> None:
    verdict = RiskGovernor().evaluate(_opportunity(risk=80.0), account_equity=100_000)
    assert verdict.status is RiskStatus.VETO
    assert any("Risk Score" in r for r in verdict.reasons)


def test_governor_veto_negative_expected_value() -> None:
    opp = _opportunity()
    opp.metrics.expected_value = -5.0
    verdict = RiskGovernor().evaluate(opp, account_equity=100_000)
    assert verdict.status is RiskStatus.VETO
    assert any("Expected value" in r for r in verdict.reasons)


def test_governor_veto_wide_spread() -> None:
    wide = _candidate(bid_low=2.0, ask_low=4.0, bid_high=0.5, ask_high=1.9)
    verdict = RiskGovernor().evaluate(_opportunity(candidate=wide), account_equity=100_000)
    assert verdict.status is RiskStatus.VETO
    assert any("Spread" in r for r in verdict.reasons)


def test_governor_veto_insufficient_buying_power() -> None:
    # Tiny account -> per-trade budget can't afford one contract.
    verdict = RiskGovernor().evaluate(_opportunity(), account_equity=1_000)
    assert verdict.status is RiskStatus.VETO
    assert any("risk budget" in r for r in verdict.reasons)


def test_governor_veto_duplicate_position() -> None:
    verdict = RiskGovernor().evaluate(
        _opportunity(),
        account_equity=100_000,
        existing_position_keys={"SPY:Bull Call Spread"},
    )
    assert verdict.status is RiskStatus.VETO
    assert any("Duplicate" in r for r in verdict.reasons)


def test_governor_veto_max_open_trades() -> None:
    verdict = RiskGovernor().evaluate(
        _opportunity(), account_equity=100_000, open_trades_count=10
    )
    assert verdict.status is RiskStatus.VETO
    assert any("Open trades" in r for r in verdict.reasons)


def test_governor_required_open_interest_vetos_when_missing() -> None:
    cand = _candidate()
    for leg in cand.legs:
        leg.contract.open_interest = None
    limits = RiskLimits(require_open_interest=True)
    verdict = RiskGovernor(limits).evaluate(
        _opportunity(candidate=cand), account_equity=100_000
    )
    assert verdict.status is RiskStatus.VETO
    assert any("Open interest" in r for r in verdict.reasons)
