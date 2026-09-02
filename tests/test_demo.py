"""Tests for the offline demo data adapter and demo pipeline."""

from __future__ import annotations

import pytest

from backend.alpaca.demo_adapter import DemoAdapter
from backend.alpaca.mcp_adapter import get_adapter
from backend.core.config import Settings
from backend.execution.decision import DecisionEngine
from backend.execution.models import DecisionOutcome
from backend.market.models import MarketRegime
from backend.quant.pipeline import generate_opportunities


def _demo_settings(tmp_path) -> Settings:
    return Settings(
        ALPACA_API_KEY="",
        ALPACA_SECRET_KEY="",
        USE_DEMO_DATA=True,
        DEMO_MODE=True,
        DATABASE_URL=f"sqlite:///{(tmp_path / 'demo.db').as_posix()}",
    )


def test_get_adapter_returns_demo_when_flagged(tmp_path) -> None:
    adapter = get_adapter(_demo_settings(tmp_path))
    assert isinstance(adapter, DemoAdapter)


@pytest.mark.asyncio
async def test_demo_chain_and_account(tmp_path) -> None:
    adapter = DemoAdapter(_demo_settings(tmp_path))
    account = await adapter.get_account()
    clock = await adapter.get_clock()
    chain = await adapter.get_option_chain("SPY")
    assert account.status == "ACTIVE"
    assert clock.is_open is True
    assert chain.count > 0
    assert all(c.mid and c.mid > 0 for c in chain.contracts)


@pytest.mark.asyncio
async def test_demo_pipeline_yields_opportunities(tmp_path) -> None:
    adapter = DemoAdapter(_demo_settings(tmp_path))
    result = await generate_opportunities(adapter, "SPY")
    assert result.context.regime is MarketRegime.BULLISH
    assert len(result.opportunities) > 0
    assert result.opportunities[0].alpha_score > 0


@pytest.mark.asyncio
async def test_demo_pipeline_produces_an_execute(tmp_path) -> None:
    adapter = DemoAdapter(_demo_settings(tmp_path))
    result = await generate_opportunities(adapter, "SPY")
    account = await adapter.get_account()
    engine = DecisionEngine()
    outcomes = [
        (await engine.decide(o, account_equity=account.equity)).decision
        for o in result.opportunities[:10]
    ]
    assert DecisionOutcome.EXECUTE in outcomes
