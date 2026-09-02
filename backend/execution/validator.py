"""Trade Validator — the pre-flight gate before any order is sent.

Alpha Engine + Adversarial + Risk Governor must have converged (decision =
EXECUTE) and every mechanical precondition must hold. If anything is off, ORION
does NOT execute. Paper trading is enforced here as a hard invariant.
"""

from __future__ import annotations

from backend.alpaca.models import Account, Clock
from backend.core.config import Settings, get_settings
from backend.core.logging import get_logger
from backend.execution.models import (
    DecisionOutcome,
    FinalDecision,
    ValidationCheck,
    ValidationResult,
)
from backend.quant.models import Opportunity

logger = get_logger("execution.validator")


def client_order_id_for(opportunity: Opportunity) -> str:
    """Deterministic client_order_id so retries can never duplicate an order."""
    return f"orion-{opportunity.id}"


class TradeValidator:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def validate(
        self,
        opportunity: Opportunity,
        decision: FinalDecision,
        account: Account,
        clock: Clock | None = None,
        existing_client_order_ids: set[str] | None = None,
    ) -> ValidationResult:
        existing_client_order_ids = existing_client_order_ids or set()
        checks: list[ValidationCheck] = []
        reasons: list[str] = []

        def record(name: str, passed: bool, detail: str, *, hard: bool = True) -> None:
            checks.append(ValidationCheck(name=name, passed=passed, detail=detail))
            if hard and not passed:
                reasons.append(detail)

        cand = opportunity.candidate

        # Paper trading is a hard invariant.
        record(
            "paper_trading",
            self._settings.alpaca_paper_trade is True,
            "Paper trading enforced" if self._settings.alpaca_paper_trade else "Live trading is forbidden",
        )
        record(
            "decision_execute",
            decision.decision is DecisionOutcome.EXECUTE,
            f"Decision is {decision.decision.value}",
        )
        record(
            "risk_governor_pass",
            decision.risk_governor == "PASS",
            f"Risk Governor {decision.risk_governor}",
        )
        record("symbol", bool(opportunity.symbol), f"Symbol '{opportunity.symbol}'")

        # Legs / quotes.
        legs_ok = True
        for leg in cand.legs:
            c = leg.contract
            if not c.symbol or c.strike <= 0 or c.mid is None or c.mid <= 0:
                legs_ok = False
            if c.bid is not None and c.ask is not None and c.bid > c.ask:
                legs_ok = False
        record("legs_valid", legs_ok, "All legs have valid symbol/strike/quote")

        record("max_loss_known", cand.max_loss > 0, f"Max loss ${cand.max_loss:.2f}")
        record(
            "position_size",
            decision.preview.contracts >= 1,
            f"Sized {decision.preview.contracts} contract(s)",
        )
        record(
            "account_active",
            not account.trading_blocked,
            "Account trading not blocked" if not account.trading_blocked else "Account trading blocked",
        )

        # Buying power for debits.
        if cand.is_debit:
            need = decision.preview.total_debit_credit
            record(
                "buying_power",
                account.buying_power >= need,
                f"Buying power ${account.buying_power:.2f} vs debit ${need:.2f}",
            )

        # Duplicate protection.
        coid = client_order_id_for(opportunity)
        record(
            "duplicate_order",
            coid not in existing_client_order_ids,
            f"client_order_id {coid} already exists" if coid in existing_client_order_ids
            else f"client_order_id {coid} is unique",
        )

        # Market clock — hard only when we would submit a real order.
        if clock is not None:
            market_ok = clock.is_open or self._settings.demo_mode
            record(
                "market_open",
                market_ok,
                "Market open" if clock.is_open else ("Market closed (demo simulate)" if self._settings.demo_mode else "Market closed"),
                hard=not self._settings.demo_mode,
            )

        ready = not reasons
        logger.info("validation", extra={"symbol": opportunity.symbol, "ready": ready})
        return ValidationResult(ready=ready, reasons=reasons, checks=checks)
