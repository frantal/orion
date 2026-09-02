"""Tests for the Performance Engine, Replay and Backtesting engines."""

from __future__ import annotations

import pytest

from backend.alpaca.models import OptionType
from backend.backtesting.engine import BacktestEngine, simulate_candidate
from backend.backtesting.replay import ReplayScenario, replay, replay_scenarios
from backend.core.database import get_connection, init_db
from backend.market.models import MarketRegime
from backend.options.spreads import build_bull_call_spread
from backend.portfolio.performance import compute_performance
from backend.quant.expected_value import evaluate
from backend.quant.models import Opportunity, QuantMetrics
from backend.journal.decisions import DecisionJournal
from tests.conftest import make_contract


def _spread():
    lower = make_contract(100, OptionType.CALL, bid=2.9, ask=3.1)
    higher = make_contract(105, OptionType.CALL, bid=1.1, ask=1.3)
    cand = build_bull_call_spread(lower, higher, dte=30)
    assert cand is not None
    return cand


# --- Performance stats ---

def test_performance_basic() -> None:
    stats = compute_performance([100, -50, 100, -50])
    assert stats.num_trades == 4
    assert stats.wins == 2 and stats.losses == 2
    assert stats.win_rate == 0.5
    assert stats.total_pnl == 100
    assert stats.avg_win == 100 and stats.avg_loss == -50
    assert stats.expectancy == 25
    assert stats.profit_factor == 2.0
    assert stats.max_drawdown == 50
    assert stats.sharpe is not None


def test_performance_empty() -> None:
    stats = compute_performance([])
    assert stats.num_trades == 0
    assert stats.profit_factor is None
    assert stats.sharpe is None


def test_performance_no_losses() -> None:
    stats = compute_performance([10, 20, 30])
    assert stats.profit_factor is None
    assert stats.max_drawdown == 0


# --- Replay (deterministic) ---

def test_replay_matches_payoff() -> None:
    cand = _spread()
    pnls = replay(cand, [90.0, 110.0])
    assert pnls[0] == pytest.approx(-180.0)
    assert pnls[1] == pytest.approx(320.0)


def test_replay_scenarios_performance() -> None:
    cand = _spread()
    scenarios = [ReplayScenario(cand, 110.0), ReplayScenario(cand, 90.0)]
    stats = replay_scenarios(scenarios)
    assert stats.num_trades == 2
    assert stats.win_rate == 0.5


# --- Monte-Carlo backtest ---

def test_simulate_bounds_and_determinism() -> None:
    cand = _spread()
    a = simulate_candidate(cand, spot=100, iv=0.2, samples=5000, seed=7)
    b = simulate_candidate(cand, spot=100, iv=0.2, samples=5000, seed=7)
    assert a == b  # reproducible
    assert all(-180.01 <= p <= 320.01 for p in a)


def test_simulate_expectancy_near_analytic() -> None:
    cand = _spread()
    analytic = evaluate(cand, spot=100, iv=0.2).expected_value
    pnls = simulate_candidate(cand, spot=100, iv=0.2, samples=40000, seed=7)
    sim_ev = sum(pnls) / len(pnls)
    assert abs(sim_ev - analytic) < 20


def test_backtest_engine_report() -> None:
    cand = _spread()
    metrics = QuantMetrics(
        probability_of_profit=0.5, expected_value=20.0, risk_reward=1.75,
        avg_win=200, avg_loss=-150, liquidity_score=90, volatility_score=70,
        implied_volatility=0.2, alpha_score=80, risk_score=25, confidence=70,
    )
    opp = Opportunity(symbol="SPY", candidate=cand, metrics=metrics, market_regime=MarketRegime.BULLISH)
    report = BacktestEngine().run([opp], spot=100.0, samples=3000)
    assert report.symbol == "SPY"
    assert len(report.per_strategy) == 1
    assert report.aggregate.num_trades == 3000
    assert 0.0 <= report.aggregate.win_rate <= 1.0


# --- Decision journal search ---

def _insert_decision(settings, symbol, decision) -> None:
    with get_connection(settings) as conn:
        conn.execute(
            "INSERT INTO decisions (created_at, symbol, strategy, decision, pnl) "
            "VALUES (?, ?, ?, ?, ?)",
            ("2026-01-01T00:00:00Z", symbol, "Bull Call Spread", decision, 50.0 if decision == "EXECUTE" else None),
        )


def test_journal_search_and_counts(tmp_settings) -> None:
    init_db(tmp_settings)
    _insert_decision(tmp_settings, "SPY", "EXECUTE")
    _insert_decision(tmp_settings, "QQQ", "NO_TRADE")
    journal = DecisionJournal(tmp_settings)
    assert len(journal.search(symbol="SPY")) == 1
    assert len(journal.search(decision="NO_TRADE")) == 1
    counts = journal.decision_counts()
    assert counts.get("EXECUTE") == 1 and counts.get("NO_TRADE") == 1
    assert journal.performance_pnls() == [50.0]
