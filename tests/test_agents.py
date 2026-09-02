"""Tests for the generative layer: AI Analyst, Adversarial Agent, LLM validation."""

from __future__ import annotations

import pytest

from backend.agents.adversarial import AdversarialAgent
from backend.agents.analyst import AIAnalyst
from backend.agents.llm import LLMClient
from backend.agents.models import (
    AdversarialAction,
    AdversarialOutput,
    AnalystOutput,
    Recommendation,
)
from backend.agents.options_agent import OptionsAlphaAgent
from backend.alpaca.models import OptionType
from backend.core.exceptions import LLMOutputValidationError, LLMUnavailableError
from backend.market.models import MarketRegime
from backend.options.spreads import build_bull_call_spread
from backend.quant.models import Opportunity, QuantMetrics
from tests.conftest import make_contract


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


class _FakeLLM:
    def __init__(self, available=True, result=None, error=None):
        self._available = available
        self._result = result
        self._error = error

    @property
    def available(self) -> bool:
        return self._available

    async def complete_json(self, system_prompt, user_payload, schema):
        if self._error is not None:
            raise self._error
        return self._result


# --- LLM output validation ---

def test_llm_validate_accepts_valid_json() -> None:
    content = '{"thesis": "Solid setup", "confidence": 72, "recommendation": "TRADE"}'
    out = LLMClient.validate(content, AnalystOutput)
    assert out.recommendation is Recommendation.TRADE
    assert out.confidence == 72


def test_llm_validate_normalizes_recommendation() -> None:
    content = '{"thesis": "abc", "confidence": 50, "recommendation": "no trade"}'
    out = LLMClient.validate(content, AnalystOutput)
    assert out.recommendation is Recommendation.NO_TRADE


def test_llm_validate_rejects_non_json() -> None:
    with pytest.raises(LLMOutputValidationError):
        LLMClient.validate("not json at all", AnalystOutput)


def test_llm_validate_rejects_missing_fields() -> None:
    with pytest.raises(LLMOutputValidationError):
        LLMClient.validate('{"confidence": 50}', AnalystOutput)


def test_llm_validate_rejects_out_of_range_confidence() -> None:
    content = '{"thesis": "abc", "confidence": 250, "recommendation": "TRADE"}'
    with pytest.raises(LLMOutputValidationError):
        LLMClient.validate(content, AnalystOutput)


# --- Deterministic fallback (no LLM configured) ---

@pytest.mark.asyncio
async def test_analyst_deterministic_when_no_llm() -> None:
    analyst = AIAnalyst(_FakeLLM(available=False))
    out = await analyst.analyze(_opportunity())
    assert isinstance(out, AnalystOutput)
    assert out.source == "deterministic"
    assert out.recommendation is Recommendation.TRADE


@pytest.mark.asyncio
async def test_analyst_no_trade_on_low_alpha() -> None:
    analyst = AIAnalyst(_FakeLLM(available=False))
    out = await analyst.analyze(_opportunity(alpha=40.0, ev=-1.0, pop=0.2))
    assert out.recommendation is Recommendation.NO_TRADE


@pytest.mark.asyncio
async def test_analyst_falls_back_on_invalid_llm_output() -> None:
    fake = _FakeLLM(available=True, error=LLMOutputValidationError("bad"))
    out = await AIAnalyst(fake).analyze(_opportunity())
    assert out.source == "deterministic"


@pytest.mark.asyncio
async def test_analyst_uses_llm_when_valid() -> None:
    valid = AnalystOutput(
        thesis="LLM thesis", confidence=80, recommendation=Recommendation.TRADE
    )
    out = await AIAnalyst(_FakeLLM(available=True, result=valid)).analyze(_opportunity())
    assert out.source == "llm"
    assert out.thesis == "LLM thesis"


# --- Adversarial ---

@pytest.mark.asyncio
async def test_adversarial_deterministic_shape() -> None:
    out = await AdversarialAgent(_FakeLLM(available=False)).analyze(_opportunity())
    assert isinstance(out, AdversarialOutput)
    assert 0.0 <= out.alpha_penalty <= 30.0
    assert out.recommended_action in AdversarialAction


@pytest.mark.asyncio
async def test_adversarial_rejects_weak_trade() -> None:
    out = await AdversarialAgent(_FakeLLM(available=False)).analyze(
        _opportunity(pop=0.2, risk=55.0, liquidity=40.0)
    )
    assert out.recommended_action is AdversarialAction.REJECT
    assert out.alpha_penalty > 0


# --- Composite agent ---

@pytest.mark.asyncio
async def test_options_alpha_agent_adjusts_alpha() -> None:
    opp = _opportunity(pop=0.3, risk=55.0, liquidity=50.0)
    assessment = await OptionsAlphaAgent(_FakeLLM(available=False)).analyze(opp)
    assert assessment.adjusted_alpha_score <= assessment.original_alpha_score
    assert assessment.llm_used is False
    expected = round(max(0.0, opp.metrics.alpha_score - assessment.adversarial.alpha_penalty), 2)
    assert assessment.adjusted_alpha_score == pytest.approx(expected)


# --- Localization (PT) ---

@pytest.mark.asyncio
async def test_analyst_portuguese_thesis() -> None:
    out = await AIAnalyst(_FakeLLM(available=False)).analyze(_opportunity(), lang="pt")
    assert "está alinhada" in out.thesis
    assert any("Probabilidade" in e or "Valor esperado" in e for e in out.evidence)


@pytest.mark.asyncio
async def test_adversarial_portuguese_counter() -> None:
    out = await AdversarialAgent(_FakeLLM(available=False)).analyze(
        _opportunity(pop=0.2, risk=55.0, liquidity=40.0), lang="pt"
    )
    assert "pode estar sobrevalorizada" in out.counter_thesis


@pytest.mark.asyncio
async def test_analyst_defaults_to_english() -> None:
    out = await AIAnalyst(_FakeLLM(available=False)).analyze(_opportunity())
    assert "aligns with" in out.thesis
