"""Tests for the Decision Engine, Trade Validator and Execution Engine."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.alpaca.models import Account, Clock, OptionType
from backend.core.config import Settings
from backend.core.database import init_db
from backend.execution.decision import DecisionEngine
from backend.execution.executor import ExecutionEngine
from backend.execution.models import DecisionOutcome, ExecutionStatus
from backend.execution.validator import TradeValidator, client_order_id_for
from backend.journal.audit import AuditLogger
from backend.market.models import MarketRegime
from backend.options.spreads import build_bull_call_spread
from backend.quant.models import Opportunity, QuantMetrics
from tests.conftest import make_contract


class _FakeLLM:
    available = False

    async def complete_json(self, *a, **k):  # pragma: no cover - never called
        raise AssertionError("LLM must not be used")


def _opportunity(*, alpha=85.0, risk=25.0, pop=0.6, ev=20.0, liquidity=90.0) -> Opportunity:
    lower = make_contract(100, OptionType.CALL, bid=2.96, ask=3.04)
    higher = make_contract(105, OptionType.CALL, bid=1.18, ask=1.22)
    cand = build_bull_call_spread(lower, higher, dte=30)
    assert cand is not None
    metrics = QuantMetrics(
        probability_of_profit=pop,
        expected_value=ev,
        risk_reward=1.75,
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
        symbol="SPY", candidate=cand, metrics=metrics, market_regime=MarketRegime.BULLISH
    )


def _account(buying_power=400_000.0, blocked=False) -> Account:
    return Account(
        account_number="PA1",
        status="ACTIVE",
        currency="USD",
        equity=100_000.0,
        cash=100_000.0,
        buying_power=buying_power,
        portfolio_value=100_000.0,
        trading_blocked=blocked,
    )


def _clock(is_open=True) -> Clock:
    now = datetime.now(timezone.utc)
    return Clock(timestamp=now, is_open=is_open, next_open=now, next_close=now)


def _engine(tmp_settings) -> DecisionEngine:
    from backend.agents.options_agent import OptionsAlphaAgent

    return DecisionEngine(
        agent=OptionsAlphaAgent(_FakeLLM()),
        audit=AuditLogger(tmp_settings),
    )


# --- Decision Engine ---

@pytest.mark.asyncio
async def test_decision_execute_on_good_opportunity(tmp_settings) -> None:
    init_db(tmp_settings)
    final = await _engine(tmp_settings).decide(_opportunity(), account_equity=100_000)
    assert final.decision is DecisionOutcome.EXECUTE
    assert final.risk_governor == "PASS"
    assert final.execution_status is ExecutionStatus.READY
    assert final.preview.contracts >= 1
    assert final.preview.action == "EXECUTE PAPER TRADE"


@pytest.mark.asyncio
async def test_decision_no_trade_on_low_alpha(tmp_settings) -> None:
    init_db(tmp_settings)
    final = await _engine(tmp_settings).decide(
        _opportunity(alpha=45.0, ev=-1.0, pop=0.2), account_equity=100_000
    )
    assert final.decision is DecisionOutcome.NO_TRADE
    assert final.execution_status is ExecutionStatus.NO_TRADE
    assert final.reason


@pytest.mark.asyncio
async def test_decision_no_trade_on_tiny_account(tmp_settings) -> None:
    init_db(tmp_settings)
    final = await _engine(tmp_settings).decide(_opportunity(), account_equity=1_000)
    assert final.decision is DecisionOutcome.NO_TRADE


# --- Trade Validator ---

@pytest.mark.asyncio
async def test_validator_ready_for_good_decision(tmp_settings) -> None:
    init_db(tmp_settings)
    opp = _opportunity()
    final = await _engine(tmp_settings).decide(opp, account_equity=100_000)
    result = TradeValidator(tmp_settings).validate(opp, final, account=_account(), clock=_clock())
    assert result.ready is True


@pytest.mark.asyncio
async def test_validator_blocks_when_paper_disabled(tmp_settings) -> None:
    init_db(tmp_settings)
    opp = _opportunity()
    final = await _engine(tmp_settings).decide(opp, account_equity=100_000)
    live = Settings(ALPACA_PAPER_TRADE=False, DEMO_MODE=True, DATABASE_URL=tmp_settings.database_url)
    result = TradeValidator(live).validate(opp, final, account=_account(), clock=_clock())
    assert result.ready is False
    assert any("Live trading" in r for r in result.reasons)


@pytest.mark.asyncio
async def test_validator_blocks_duplicate(tmp_settings) -> None:
    init_db(tmp_settings)
    opp = _opportunity()
    final = await _engine(tmp_settings).decide(opp, account_equity=100_000)
    coid = client_order_id_for(opp)
    result = TradeValidator(tmp_settings).validate(
        opp, final, account=_account(), clock=_clock(), existing_client_order_ids={coid}
    )
    assert result.ready is False
    assert any("already exists" in r for r in result.reasons)


# --- Execution Engine (demo) ---

@pytest.mark.asyncio
async def test_execute_demo_simulates_and_dedups(tmp_settings) -> None:
    init_db(tmp_settings)
    opp = _opportunity()
    final = await _engine(tmp_settings).decide(opp, account_equity=100_000)
    engine = ExecutionEngine(settings=tmp_settings, audit=AuditLogger(tmp_settings))

    first = await engine.execute(opp, final)
    assert first.status is ExecutionStatus.PAPER_SIMULATED
    assert first.broker_order_id is not None

    # Retry with the same opportunity must NOT create a second order.
    second = await engine.execute(opp, final)
    assert second.status is ExecutionStatus.REJECTED
    assert "Duplicate" in second.detail


@pytest.mark.asyncio
async def test_execute_persists_order_row(tmp_settings) -> None:
    from backend.core.database import get_connection

    init_db(tmp_settings)
    opp = _opportunity()
    final = await _engine(tmp_settings).decide(opp, account_equity=100_000)
    await ExecutionEngine(settings=tmp_settings, audit=AuditLogger(tmp_settings)).execute(opp, final)

    with get_connection(tmp_settings) as conn:
        row = conn.execute(
            "SELECT client_order_id, status FROM orders WHERE symbol = 'SPY'"
        ).fetchone()
    assert row is not None
    assert row["status"] == ExecutionStatus.PAPER_SIMULATED.value
