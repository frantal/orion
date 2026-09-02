"""Adversarial Agent.

A core ORION feature: after the Alpha Engine proposes an opportunity, this agent
tries to prove it WRONG. Like the analyst, it uses the LLM when available but
always validates output and falls back to a deterministic critique. Its
``alpha_penalty`` can reduce the opportunity's Alpha Score before the Risk
Governor sees it. It has no execution authority.
"""

from __future__ import annotations

from backend.agents.base import TradingAgent, opportunity_summary
from backend.agents.llm import LLMClient
from backend.agents.models import AdversarialAction, AdversarialOutput
from backend.core.exceptions import LLMOutputValidationError, LLMUnavailableError
from backend.core.i18n import L, normalize_language, regime_name, strategy_name
from backend.core.logging import get_logger
from backend.quant.models import Opportunity, clamp

logger = get_logger("agents.adversarial")

SYSTEM_PROMPT = (
    "You are ORION's Adversarial Agent. Your job is to try to prove this options "
    "trade is WRONG. You receive STRUCTURED, pre-computed quantitative data. Identify "
    "what the thesis ignores, the worst case, mispriced volatility, liquidity risk, "
    "and whether the edge is illusory. Return ONLY a JSON object with fields: "
    "counter_thesis (string), failure_modes (string[]), risk_factors (string[]), "
    "main_reason_against (string), confidence (number 0-100 that the trade is flawed), "
    "recommended_action (one of PROCEED, REDUCE, REJECT), alpha_penalty (number 0-30, "
    "points to deduct from the Alpha Score). Be skeptical and grounded in the numbers."
)

_LANG_INSTRUCTION = {
    "pt": " Write all natural-language fields in European Portuguese (pt-PT).",
}


class AdversarialAgent(TradingAgent):
    name = "adversarial_agent"

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()

    async def analyze(self, opportunity: Opportunity, lang: str = "en") -> AdversarialOutput:
        lang = normalize_language(lang)
        summary = opportunity_summary(opportunity)
        if self._llm.available:
            try:
                prompt = SYSTEM_PROMPT + _LANG_INSTRUCTION.get(lang, "")
                output = await self._llm.complete_json(prompt, summary, AdversarialOutput)
                output.source = "llm"
                logger.info("adversarial llm ok", extra={"symbol": opportunity.symbol})
                return output
            except (LLMUnavailableError, LLMOutputValidationError) as exc:
                logger.warning("adversarial falling back", extra={"error": str(exc)})
        return self._deterministic(opportunity, lang)

    @staticmethod
    def _deterministic(opportunity: Opportunity, lang: str = "en") -> AdversarialOutput:
        m = opportunity.metrics
        cand = opportunity.candidate

        risk_factors: list[str] = []
        penalty = 0.0

        if m.probability_of_profit < 0.5:
            risk_factors.append(
                L(lang,
                  f"Probability of profit is only {m.probability_of_profit:.0%}",
                  f"A probabilidade de lucro é de apenas {m.probability_of_profit:.0%}")
            )
            penalty += (0.5 - m.probability_of_profit) * 20
        if m.risk_score > 45:
            risk_factors.append(L(lang, f"Risk score {m.risk_score:.0f} is elevated", f"O score de risco {m.risk_score:.0f} é elevado"))
            penalty += (m.risk_score - 45) * 0.2
        if m.liquidity_score < 75:
            risk_factors.append(L(lang, f"Liquidity {m.liquidity_score:.0f} could impair execution", f"A liquidez {m.liquidity_score:.0f} pode dificultar a execução"))
            penalty += (75 - m.liquidity_score) * 0.1
        if m.expected_value < cand.max_loss * 0.05:
            risk_factors.append(L(lang, "Expected value is thin relative to capital at risk", "O valor esperado é reduzido face ao capital em risco"))
            penalty += 3
        if cand.is_debit:
            risk_factors.append(L(lang, "Long premium is exposed to IV contraction and time decay", "O prémio comprado está exposto à contração da volatilidade e ao decaimento temporal"))
        else:
            risk_factors.append(L(lang, "Short premium is exposed to an adverse gap through the short strike", "O prémio vendido está exposto a um gap adverso através do strike vendido"))

        if not risk_factors:
            risk_factors.append(L(lang, "No dominant weakness, but no trade is risk-free", "Sem fraqueza dominante, mas nenhum trade é isento de risco"))

        penalty = round(clamp(penalty, 0.0, 25.0), 2)

        if penalty >= 20 or m.probability_of_profit < 0.3:
            action = AdversarialAction.REJECT
        elif penalty >= 10:
            action = AdversarialAction.REDUCE
        else:
            action = AdversarialAction.PROCEED

        main_reason = risk_factors[0]
        strat = strategy_name(opportunity.strategy, lang)
        regime = regime_name(opportunity.market_regime.value, lang)
        counter_thesis = L(
            lang,
            (
                f"The {strat} may be overrated: {main_reason.lower()}. "
                f"With {cand.dte} days to expiration, the edge depends on timing and could "
                f"erode if the {regime} read is wrong."
            ),
            (
                f"A {strat} pode estar sobrevalorizada: {main_reason.lower()}. "
                f"Com {cand.dte} dias até ao vencimento, a vantagem depende do timing e pode "
                f"desaparecer se a leitura de {regime} estiver errada."
            ),
        )
        confidence = round(clamp(30 + penalty * 2.4, 0, 100), 2)

        return AdversarialOutput(
            counter_thesis=counter_thesis,
            failure_modes=opportunity.invalidation_conditions[:3],
            risk_factors=risk_factors,
            main_reason_against=main_reason,
            confidence=confidence,
            recommended_action=action,
            alpha_penalty=penalty,
            source="deterministic",
        )
