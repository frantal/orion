# ORION — Decision Engine

The Decision Engine is the heart of ORION. It turns raw market data into a
single, auditable verdict: **EXECUTE** (paper) or **NO TRADE**.

## Stages

| # | Stage | Type | Output |
|---|-------|------|--------|
| 1 | Market Intelligence | deterministic | market regime |
| 2 | Options Scanner | deterministic | candidate contracts |
| 3 | Quant Engine | deterministic | scores, EV, risk/reward |
| 4 | AI Analyst | generative (validated) | thesis, confidence |
| 5 | Adversarial Agent | generative (validated) | counter-thesis, failure modes |
| 6 | Risk Governor | deterministic | PASS / VETO |
| 7 | Trade Validator | deterministic | READY_FOR_EXECUTION |
| 8 | Execution | broker (paper) | order / preview |

## Principles

- **NO TRADE is first-class.** A disciplined pass is better than a low-quality
  trade. Every NO TRADE is recorded with a reason.
- **The Risk Governor is supreme.** It is deterministic and can veto any
  decision — including the LLM's — for exposure, liquidity, spread, or scores.
- **On any error or ambiguity → NO TRADE.** No failure path may trigger an
  unsafe automatic execution.

## Final decision object

```json
{
  "symbol": "SPY",
  "strategy": "Bull Call Spread",
  "alpha_score": 84,
  "risk_score": 24,
  "liquidity_score": 91,
  "expected_value": 42.0,
  "risk_reward": 1.75,
  "thesis": "...",
  "counter_thesis": "...",
  "risk_governor": "PASS",
  "decision": "EXECUTE",
  "reason": "...",
  "timestamp": "2026-09-02T10:00:00Z",
  "execution_status": "PAPER"
}
```

Stages 3–8 are implemented across Phases 3–5.
