# ORION — Risk Framework

The **Risk Governor** is a deterministic gate. It is **not** controlled by the
LLM and can **veto** any decision.

## Configurable limits (defaults, Phase 3)

| Limit | Default | Meaning |
|-------|---------|---------|
| `MAX_PORTFOLIO_RISK` | 0.02 | max fraction of equity at risk overall |
| `MAX_SINGLE_TRADE_RISK` | 0.01 | max fraction of equity per trade |
| `MIN_ALPHA_SCORE` | 70 | minimum opportunity quality |
| `MIN_LIQUIDITY_SCORE` | 60 | minimum liquidity |
| `MAX_RISK_SCORE` | 60 | maximum tolerated risk |
| `MIN_RISK_REWARD` | 1.5 | minimum reward/risk ratio |
| `MAX_SPREAD_PERCENT` | 5 | maximum bid/ask spread |
| `MIN_OPEN_INTEREST` | 100 | minimum open interest |
| `MIN_VOLUME` | 20 | minimum contract volume |

Limits live in `backend/risk/limits.py` — no magic numbers scattered in logic.

## Checks

Portfolio exposure, position size, max loss, liquidity, spread, Alpha Score,
Risk Score, market regime, duplicate positions, correlated exposure, daily loss
limit, maximum open trades.

## Result

`PASS` or `VETO` with an explicit reason. Example:

```
RISK GOVERNOR
STATUS: VETO
Reason: Expected value acceptable, but liquidity insufficient.
```

## Position sizing

```
max_position_risk = account_equity * MAX_SINGLE_TRADE_RISK
contracts         = floor(max_position_risk / max_loss_per_contract)
```

If `contracts < 1`, the opportunity is flagged as not executable — ORION never
forces a position it cannot size safely.

## Safety posture

- Paper trading only; `ALPACA_PAPER_TRADE=false` is refused.
- On any error or ambiguity → **NO TRADE**.
