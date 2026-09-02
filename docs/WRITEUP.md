# ORION — One-Page Write-Up

### Autonomous Options Alpha Agent · *"The agent that has to prove its trade."*
**Alpaca AI Trading Agents Hackathon 2026 · Paper trading only**

---

## The idea

Most trading agents go **Find → Trade**. ORION goes:

```
Find → Quantify → Explain → Attack → Risk-Check → Validate → EXECUTE / NO TRADE
```

Every candidate must *survive* an adversarial challenge and an independent risk
gate before it can reach the (paper) broker. **NO TRADE is a first-class outcome** —
ORION optimizes *decision quality*, not trade count.

## AI logic (hybrid intelligence)

ORION deliberately separates **deterministic** from **generative** intelligence:

- **Deterministic (Python, never the LLM):** market-regime classification, option
  scanning/filtering, probability of profit and expected value (numeric integration
  over a lognormal terminal distribution), Greeks/IV, liquidity, an **Alpha Score**
  (30% EV · 20% R:R · 15% liquidity · 15% vol-edge · 10% regime · 10% catalyst) and
  a **Risk Score**.
- **Generative (LLM, reasoning only):** an **AI Analyst** writes the thesis and
  recommends TRADE/WATCH/NO_TRADE; an **Adversarial Agent** tries to *prove the trade
  wrong* and can deduct from the Alpha Score. The LLM is optional — a deterministic
  fallback keeps the pipeline fully functional, and every LLM output is schema-validated
  or rejected. The LLM is never the authority on risk.

## Risk gates

- **Risk Governor** (deterministic, independent, can veto anything): min Alpha,
  min liquidity, max Risk Score, min risk/reward, **min expected value ≥ 0**, max
  spread, duplicate-position and max-open-trades checks, and per-trade / portfolio
  exposure caps.
- **Conservative position sizing:** risk per trade capped at a fraction of equity;
  fewer than one contract ⇒ not executable.
- **Trade Validator (pre-flight):** paper enforced, valid legs/quotes, known max
  loss, unique `client_order_id` (retry-safe), market-open, Risk Governor = PASS.
- **Safety invariants:** paper trading only (refuses `ALPACA_PAPER_TRADE=false`);
  on any error or ambiguity ⇒ **NO TRADE**; every decision is audited and journaled.

## Alpaca infrastructure

- **Alpaca CLI** (official `alpaca` binary) drives **account, clock, positions,
  orders and order submission** via `alpaca api …` (JSON). Single-leg (`simple`)
  and multi-leg options spreads (`mleg`) are both submitted through the CLI.
- **Alpaca Market Data (REST)** provides stock quotes/snapshots and option
  chains with Greeks/IV.
- All access is behind one adapter (`backend/alpaca/mcp_adapter.py`); the CLI vs
  REST client is swappable via `USE_ALPACA_CLI`.
- **Developed and tested on a dedicated paper account with a $100,000 balance.**

## Proven results (live)

- Multi-leg options orders **submitted and confirmed through the Alpaca CLI** on
  the paper account (e.g. a QQQ Bear Call Spread, `mleg`, accepted `new`).
- The differentiator is visible in the product: opportunities that **pass the Risk
  Governor are still turned into NO TRADE when the Adversarial Agent rejects them.**

## Stack & quality

Python 3.12 · FastAPI · NumPy/SciPy/pandas · SQLite · React + Vite dashboard
(dark, quant-styled, EN/PT) · **93 automated tests** · offline demo mode
(`USE_DEMO_DATA=true`) that runs with no keys and no network.

## Submission

- **Alpaca paper account ID (for judging): `PA3B2R5S7KPW`**
- Run: `python -m backend.main --diagnostic` → `python -m backend.main` → dashboard
  at `http://localhost:5173`. Offline demo: set `USE_DEMO_DATA=true`.
