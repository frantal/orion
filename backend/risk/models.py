"""Risk Engine models: verdicts, checks, position sizing."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class RiskStatus(str, Enum):
    PASS = "PASS"
    VETO = "VETO"


class RiskCheck(BaseModel):
    name: str
    passed: bool
    detail: str


class PositionSizing(BaseModel):
    contracts: int
    max_position_risk: float  # dollars allowed at risk for this trade
    max_loss_per_contract: float
    total_max_loss: float
    executable: bool
    reason: str | None = None


class RiskVerdict(BaseModel):
    status: RiskStatus
    reasons: list[str] = Field(default_factory=list)
    checks: list[RiskCheck] = Field(default_factory=list)
    sizing: PositionSizing | None = None

    @property
    def is_pass(self) -> bool:
        return self.status is RiskStatus.PASS
