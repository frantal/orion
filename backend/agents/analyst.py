"""AI Analyst.

Interprets the deterministic quant data and produces a qualitative thesis. It
uses the LLM when configured, but always validates the output; on any failure
(LLM unavailable or invalid output) it falls back to a deterministic,
rule-based analyst so the pipeline never depends on the LLM. The analyst has NO
execution authority — it only recommends TRADE / WATCH / NO_TRADE.
"""

from __future__ import annotations

from backend.agents.base import TradingAgent, opportunity_summary
from backend.agents.llm import LLMClient
from backend.agents.models import AnalystOutput, Recommendation
from backend.core.exceptions import LLMOutputValidationError, LLMUnavailableError
from backend.core.i18n import L, normalize_language, regime_name, strategy_name
from backend.core.logging import get_logger
from backend.quant.models import Opportunity

logger = get_logger("agents.analyst")

SYSTEM_PROMPT = (
    "You are ORION's AI Analyst. You receive STRUCTURED, pre-computed quantitative "
    "data about a single options opportunity. You MUST NOT compute numbers, invent "
    "prices, or place trades. Interpret the data and return ONLY a JSON object with "
    "these fields: thesis (string), evidence (string[]), catalysts (string[]), "
    "expected_behavior (string), invalidation (string[]), risks (string[]), why_now "
    "(string), confidence (number 0-100), recommendation (one of TRADE, WATCH, "
    "NO_TRADE). Be concise and grounded strictly in the provided numbers."
)

_LANG_INSTRUCTION = {
    "pt": " Write all natural-language fields in European Portuguese (pt-PT).",
}


class AIAnalyst(TradingAgent):
    name = "ai_analyst"

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()

    async def analyze(self, opportunity: Opportunity, lang: str = "en") -> AnalystOutput:
        lang = normalize_language(lang)
        summary = opportunity_summary(opportunity)
        if self._llm.available:
            try:
                prompt = SYSTEM_PROMPT + _LANG_INSTRUCTION.get(lang, "")
                output = await self._llm.complete_json(prompt, summary, AnalystOutput)
                output.source = "llm"
                logger.info("analyst llm ok", extra={"symbol": opportunity.symbol})
                return output
            except (LLMUnavailableError, LLMOutputValidationError) as exc:
                logger.warning("analyst falling back", extra={"error": str(exc)})
        return self._deterministic(opportunity, lang)

    @staticmethod
    def _deterministic(opportunity: Opportunity, lang: str = "en") -> AnalystOutput:
        m = opportunity.metrics
        cand = opportunity.candidate
        regime = regime_name(opportunity.market_regime.value, lang)
        strat = strategy_name(opportunity.strategy, lang)

        if m.alpha_score >= 70 and m.expected_value > 0 and m.probability_of_profit >= 0.35:
            reco = Recommendation.TRADE
        elif m.alpha_score >= 55:
            reco = Recommendation.WATCH
        else:
            reco = Recommendation.NO_TRADE

        thesis = L(
            lang,
            (
                f"{opportunity.symbol} {strat} aligns with a {regime} regime. "
                f"The structure carries positive expected value (${m.expected_value:.2f}) with a "
                f"{m.probability_of_profit:.0%} probability of profit and a {m.risk_reward:.2f} "
                f"reward-to-risk over {cand.dte} days."
            ),
            (
                f"{opportunity.symbol} {strat} está alinhada com um regime de {regime}. "
                f"A estrutura tem valor esperado positivo (${m.expected_value:.2f}), com "
                f"{m.probability_of_profit:.0%} de probabilidade de lucro e um rácio risco/retorno "
                f"de {m.risk_reward:.2f} ao longo de {cand.dte} dias."
            ),
        )
        evidence = [
            L(lang, f"Alpha Score {m.alpha_score:.0f}/100", f"Score Alpha {m.alpha_score:.0f}/100"),
            L(lang, f"Expected value ${m.expected_value:.2f}", f"Valor esperado ${m.expected_value:.2f}"),
            L(lang, f"Probability of profit {m.probability_of_profit:.0%}", f"Probabilidade de lucro {m.probability_of_profit:.0%}"),
            L(lang, f"Risk/reward {m.risk_reward:.2f}", f"Risco/retorno {m.risk_reward:.2f}"),
            L(lang, f"Liquidity score {m.liquidity_score:.0f}/100", f"Score de liquidez {m.liquidity_score:.0f}/100"),
        ]
        risks: list[str] = []
        if m.probability_of_profit < 0.5:
            risks.append(
                L(lang,
                  f"Sub-50% probability of profit ({m.probability_of_profit:.0%})",
                  f"Probabilidade de lucro inferior a 50% ({m.probability_of_profit:.0%})")
            )
        if m.risk_score > 45:
            risks.append(L(lang, f"Elevated risk score ({m.risk_score:.0f})", f"Score de risco elevado ({m.risk_score:.0f})"))
        if m.liquidity_score < 75:
            risks.append(L(lang, f"Liquidity ({m.liquidity_score:.0f}) may affect fills", f"Liquidez ({m.liquidity_score:.0f}) pode afetar a execução"))
        if not risks:
            risks.append(L(lang, "Standard time-decay and directional risk", "Risco padrão de decaimento temporal e direcional"))

        return AnalystOutput(
            thesis=thesis,
            evidence=evidence,
            catalysts=[L(lang, f"Market regime: {regime}", f"Regime de mercado: {regime}")],
            expected_behavior=L(
                lang,
                "Position benefits if the underlying moves consistent with the strategy bias before expiration.",
                "A posição beneficia se o ativo se mover no sentido da estratégia antes do vencimento.",
            ),
            invalidation=opportunity.invalidation_conditions,
            risks=risks,
            why_now=L(
                lang,
                f"Current {regime} regime and pricing yield a favourable quant profile.",
                f"O regime atual de {regime} e o preço geram um perfil quantitativo favorável.",
            ),
            confidence=m.confidence,
            recommendation=reco,
            source="deterministic",
        )
