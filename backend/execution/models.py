"""Decision & execution models.

The :class:`FinalDecision` is ORION's terminal verdict (section 45): EXECUTE
(paper) or NO_TRADE, with the full reasoning trail. Nothing here places an
order — that is the Execution Engine's job, and only after explicit validation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class DecisionOutcome(str, Enum):
    EXECUTE = "EXECUTE"
    NO_TRADE = "NO_TRADE"


class ExecutionStatus(str, Enum):
    NO_TRADE = "NO_TRADE"
    READY = "READY_FOR_EXECUTION"
    PAPER_SIMULATED = "PAPER_SIMULATED"
    PAPER_SUBMITTED = "PAPER_SUBMITTED"
    REJECTED = "REJECTED"
    ERROR = "ERROR"


class ExecutionPreview(BaseModel):
    """Human-facing preview of what would be executed (section 16)."""

    strategy: str
    underlying: str
    expiration: str
    legs: list[str]  # e.g. "BUY 540 Call"
    net_type: str  # "debit" | "credit"
    net_amount: float  # per-contract dollars
    contracts: int
    total_debit_credit: float
    max_loss: float
    max_profit: float | None
    risk_reward: float
    alpha_score: float
    risk_score: float
    liquidity_score: float
    adversarial_confidence: float
    risk_governor: str
    action: str  # "EXECUTE PAPER TRADE" | "NO TRADE"


class FinalDecision(BaseModel):
    """ORION's final decision object."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    opportunity_id: str
    symbol: str
    strategy: str
    market_regime: str

    alpha_score: float
    original_alpha_score: float
    risk_score: float
    liquidity_score: float
    expected_value: float
    risk_reward: float
    probability_of_profit: float

    thesis: str
    counter_thesis: str
    analyst_recommendation: str
    adversarial_action: str
    adversarial_confidence: float

    risk_governor: str  # PASS | VETO
    decision: DecisionOutcome
    reason: str
    execution_status: ExecutionStatus
    preview: ExecutionPreview
    order_id: str | None = None


class ValidationCheck(BaseModel):
    name: str
    passed: bool
    detail: str


class ValidationResult(BaseModel):
    ready: bool
    reasons: list[str] = Field(default_factory=list)
    checks: list[ValidationCheck] = Field(default_factory=list)


class OrderLeg(BaseModel):
    symbol: str
    side: str  # buy | sell
    ratio_qty: int = 1
    position_intent: str  # buy_to_open | sell_to_open


class OrderRequest(BaseModel):
    client_order_id: str
    symbol: str
    strategy: str
    contracts: int
    limit_price: float  # net debit (positive) or credit (as positive amount)
    is_debit: bool
    legs: list[OrderLeg]


class OrderResult(BaseModel):
    client_order_id: str
    status: ExecutionStatus
    broker_order_id: str | None = None
    detail: str = ""
