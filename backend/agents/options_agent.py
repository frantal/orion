"""OptionsAlphaAgent — the main composite agent.

Runs the AI Analyst then the Adversarial Agent over an opportunity, and applies
the adversarial ``alpha_penalty`` to produce an adjusted Alpha Score. This is the
generative half of the pipeline; the Risk Governor (deterministic) still has the
final veto downstream.
"""

from __future__ import annotations

from backend.agents.adversarial import AdversarialAgent
from backend.agents.analyst import AIAnalyst
from backend.agents.base import TradingAgent
from backend.agents.llm import LLMClient
from backend.agents.models import AlphaAssessment
from backend.core.logging import get_logger
from backend.quant.models import Opportunity, clamp

logger = get_logger("agents.options_alpha")


class OptionsAlphaAgent(TradingAgent):
    """Primary agent: analyst + adversarial challenge over an opportunity."""

    name = "options_alpha_agent"

    def __init__(self, llm: LLMClient | None = None) -> None:
        llm = llm or LLMClient()
        self._analyst = AIAnalyst(llm)
        self._adversarial = AdversarialAgent(llm)
        self._llm = llm

    async def analyze(self, opportunity: Opportunity, lang: str = "en") -> AlphaAssessment:
        analyst = await self._analyst.analyze(opportunity, lang)
        adversarial = await self._adversarial.analyze(opportunity, lang)

        original = opportunity.metrics.alpha_score
        adjusted = round(clamp(original - adversarial.alpha_penalty), 2)
        llm_used = analyst.source == "llm" or adversarial.source == "llm"

        logger.info(
            "alpha assessment",
            extra={
                "symbol": opportunity.symbol,
                "original_alpha": original,
                "adjusted_alpha": adjusted,
                "llm_used": llm_used,
            },
        )
        return AlphaAssessment(
            opportunity_id=opportunity.id,
            symbol=opportunity.symbol,
            strategy=opportunity.strategy,
            analyst=analyst,
            adversarial=adversarial,
            original_alpha_score=original,
            adjusted_alpha_score=adjusted,
            llm_used=llm_used,
        )
