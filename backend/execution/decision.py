"""Decision Engine — the convergence point.

Combines the generative assessment (AI Analyst + Adversarial Agent) with the
deterministic Risk Governor to produce a single :class:`FinalDecision`
(EXECUTE / NO_TRADE). The adversarial ``alpha_penalty`` is applied BEFORE the
governor sees the opportunity, so a challenged trade can be vetoed on merit.
NO_TRADE is a first-class outcome. This engine never places an order.
"""

from __future__ import annotations

from backend.agents.models import AdversarialAction, Recommendation
from backend.agents.options_agent import OptionsAlphaAgent
from backend.core.i18n import L, normalize_language, token
from backend.core.logging import get_logger
from backend.execution.models import (
    DecisionOutcome,
    ExecutionPreview,
    ExecutionStatus,
    FinalDecision,
)
from backend.journal.audit import AuditLogger
from backend.options.models import OptionType
from backend.quant.models import Opportunity
from backend.risk.governor import RiskGovernor
from backend.risk.models import RiskVerdict

logger = get_logger("execution.decision")


class DecisionEngine:
    """Produces ORION's final EXECUTE / NO_TRADE decision for an opportunity."""

    def __init__(
        self,
        agent: OptionsAlphaAgent | None = None,
        governor: RiskGovernor | None = None,
        audit: AuditLogger | None = None,
    ) -> None:
        self._agent = agent or OptionsAlphaAgent()
        self._governor = governor or RiskGovernor()
        self._audit = audit or AuditLogger()

    async def decide(
        self,
        opportunity: Opportunity,
        account_equity: float,
        open_trades_count: int = 0,
        existing_position_keys: set[str] | None = None,
        lang: str = "en",
    ) -> FinalDecision:
        lang = normalize_language(lang)
        self._audit.log("DECISION_ENGINE", "start", input_data={"symbol": opportunity.symbol})

        assessment = await self._agent.analyze(opportunity, lang)
        self._audit.log(
            "AI_ANALYST",
            assessment.analyst.recommendation.value,
            output_data={"confidence": assessment.analyst.confidence, "source": assessment.analyst.source},
        )
        self._audit.log(
            "ADVERSARIAL_AGENT",
            assessment.adversarial.recommended_action.value,
            output_data={"penalty": assessment.adversarial.alpha_penalty},
        )

        # Apply the adversarial penalty before the Risk Governor evaluates.
        adjusted = opportunity.model_copy(deep=True)
        adjusted.metrics.alpha_score = assessment.adjusted_alpha_score

        verdict = self._governor.evaluate(
            adjusted, account_equity, open_trades_count, existing_position_keys, lang
        )
        self._audit.log("RISK_GOVERNOR", verdict.status.value, output_data={"reasons": verdict.reasons})

        outcome, reason = self._resolve(assessment, verdict, lang)
        preview = self._build_preview(opportunity, assessment, verdict, outcome)

        decision = FinalDecision(
            opportunity_id=opportunity.id,
            symbol=opportunity.symbol,
            strategy=opportunity.strategy,
            market_regime=opportunity.market_regime.value,
            alpha_score=assessment.adjusted_alpha_score,
            original_alpha_score=assessment.original_alpha_score,
            risk_score=opportunity.metrics.risk_score,
            liquidity_score=opportunity.metrics.liquidity_score,
            expected_value=opportunity.metrics.expected_value,
            risk_reward=opportunity.metrics.risk_reward,
            probability_of_profit=opportunity.metrics.probability_of_profit,
            thesis=assessment.analyst.thesis,
            counter_thesis=assessment.adversarial.counter_thesis,
            analyst_recommendation=assessment.analyst.recommendation.value,
            adversarial_action=assessment.adversarial.recommended_action.value,
            adversarial_confidence=assessment.adversarial.confidence,
            risk_governor=verdict.status.value,
            decision=outcome,
            reason=reason,
            execution_status=(
                ExecutionStatus.READY if outcome is DecisionOutcome.EXECUTE else ExecutionStatus.NO_TRADE
            ),
            preview=preview,
        )
        self._audit.log("DECISION_ENGINE", outcome.value, output_data={"reason": reason})
        logger.info("decision made", extra={"symbol": opportunity.symbol, "decision": outcome.value})
        return decision

    @staticmethod
    def _resolve(assessment, verdict: RiskVerdict, lang: str = "en") -> tuple[DecisionOutcome, str]:
        blocks: list[str] = []
        if assessment.analyst.recommendation is Recommendation.NO_TRADE:
            blocks.append(L(lang, "AI Analyst recommends NO_TRADE", "O Analista IA recomenda NÃO OPERAR"))
        if assessment.adversarial.recommended_action is AdversarialAction.REJECT:
            blocks.append(L(lang, "Adversarial Agent rejected the trade", "O Agente Adversarial rejeitou o trade"))
        if not verdict.is_pass:
            prefix = L(lang, "Risk Governor", "Governador de Risco")
            blocks.extend(f"{prefix}: {r}" for r in verdict.reasons)

        if blocks:
            return DecisionOutcome.NO_TRADE, "; ".join(blocks)
        reco = token(assessment.analyst.recommendation.value, lang)
        action = token(assessment.adversarial.recommended_action.value, lang)
        return (
            DecisionOutcome.EXECUTE,
            L(
                lang,
                f"Risk Governor PASS; analyst {reco}; adversarial {action}.",
                f"Governador de Risco APROVADO; analista {reco}; adversarial {action}.",
            ),
        )

    @staticmethod
    def _build_preview(
        opportunity: Opportunity,
        assessment,
        verdict: RiskVerdict,
        outcome: DecisionOutcome,
    ) -> ExecutionPreview:
        cand = opportunity.candidate
        m = opportunity.metrics
        contracts = verdict.sizing.contracts if verdict.sizing else 0
        legs = [
            f"{leg.action.value.upper()} {leg.contract.strike:g} "
            f"{'Call' if leg.contract.option_type is OptionType.CALL else 'Put'}"
            for leg in cand.legs
        ]
        net_amount = round(abs(cand.net_premium), 4)
        return ExecutionPreview(
            strategy=opportunity.strategy,
            underlying=opportunity.symbol,
            expiration=cand.expiration.isoformat(),
            legs=legs,
            net_type="debit" if cand.is_debit else "credit",
            net_amount=net_amount,
            contracts=contracts,
            total_debit_credit=round(net_amount * 100 * contracts, 2),
            max_loss=round(cand.max_loss * max(contracts, 1), 2),
            max_profit=round(cand.max_profit * max(contracts, 1), 2) if cand.max_profit is not None else None,
            risk_reward=m.risk_reward,
            alpha_score=assessment.adjusted_alpha_score,
            risk_score=m.risk_score,
            liquidity_score=m.liquidity_score,
            adversarial_confidence=assessment.adversarial.confidence,
            risk_governor=verdict.status.value,
            action="EXECUTE PAPER TRADE" if outcome is DecisionOutcome.EXECUTE else "NO TRADE",
        )
