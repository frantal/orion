"""Agent output models with strict validation.

The generative layer never gets execution authority. Everything an LLM produces
must validate against these schemas; anything that fails is rejected and the
deterministic fallback is used instead. Confidence values are 0-100.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Recommendation(str, Enum):
    TRADE = "TRADE"
    WATCH = "WATCH"
    NO_TRADE = "NO_TRADE"


class AdversarialAction(str, Enum):
    PROCEED = "PROCEED"
    REDUCE = "REDUCE"
    REJECT = "REJECT"


def _coerce_enum(value: str) -> str:
    return str(value).strip().upper().replace(" ", "_").replace("-", "_")


class AnalystOutput(BaseModel):
    """Structured output of the AI Analyst (section 12)."""

    thesis: str = Field(min_length=3)
    evidence: list[str] = Field(default_factory=list)
    catalysts: list[str] = Field(default_factory=list)
    expected_behavior: str = ""
    invalidation: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    why_now: str = ""
    confidence: float = Field(ge=0.0, le=100.0)
    recommendation: Recommendation
    source: str = Field(default="llm", description="'llm' or 'deterministic'")

    @field_validator("recommendation", mode="before")
    @classmethod
    def _norm_reco(cls, v: object) -> object:
        return _coerce_enum(v) if isinstance(v, str) and not isinstance(v, Enum) else v


class AdversarialOutput(BaseModel):
    """Structured output of the Adversarial Agent (section 13)."""

    counter_thesis: str = Field(min_length=3)
    failure_modes: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    main_reason_against: str = ""
    confidence: float = Field(ge=0.0, le=100.0, description="Confidence the trade is flawed")
    recommended_action: AdversarialAction
    alpha_penalty: float = Field(default=0.0, ge=0.0, le=30.0)
    source: str = Field(default="llm")

    @field_validator("recommended_action", mode="before")
    @classmethod
    def _norm_action(cls, v: object) -> object:
        return _coerce_enum(v) if isinstance(v, str) and not isinstance(v, Enum) else v


class AlphaAssessment(BaseModel):
    """Combined analyst + adversarial assessment of an opportunity."""

    opportunity_id: str
    symbol: str
    strategy: str
    analyst: AnalystOutput
    adversarial: AdversarialOutput
    original_alpha_score: float
    adjusted_alpha_score: float
    llm_used: bool
