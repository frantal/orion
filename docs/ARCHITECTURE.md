# ORION — Architecture

## Problem

Most trading agents jump straight from *find* to *trade*. They lean on an LLM
for reasoning **and** for math, which makes them non-deterministic, unauditable,
and unsafe. ORION solves this by separating **deterministic intelligence** from
**generative intelligence** and forcing every candidate through an adversarial,
risk-governed decision pipeline.

## Solution

ORION is an autonomous options alpha agent that must **prove its trade**. It
produces one of two first-class outcomes: `EXECUTE` (paper) or `NO TRADE`.

## Hybrid intelligence

| Deterministic (Python) | Generative (LLM) |
|------------------------|------------------|
| Pricing, Greeks, probability | Thesis |
| Expected value, risk/reward | Explanation |
| Liquidity, spread, scoring | News interpretation |
| Position sizing | Adversarial critique |
| Risk limits, validation | Market narrative |

The financial math never depends on the LLM. If the LLM is unavailable, the
deterministic pipeline still runs and can still reach a safe decision.

## Pipeline

```
Market Data
  → Market Intelligence      (regime classifier — deterministic)
  → Options Scanner          (chain filtering — deterministic)
  → Quant Engine             (EV, scores — deterministic)
  → Alpha Engine / AI Analyst (thesis — generative, validated)
  → Adversarial Agent        (attack the thesis — generative, validated)
  → Risk Governor            (veto authority — deterministic)
  → Trade Validator          (pre-flight checks — deterministic)
  → Execution Engine         (Alpaca paper trading)
  → Portfolio Monitor / Performance / Journal
```

## Module layout

```
backend/
  core/        config, logging, exceptions, database, diagnostics
  alpaca/      MCP adapter, client, models          (Phase 2)
  market/      intelligence, scanner, regime         (Phase 2/3)
  options/     chain, scanner, greeks, spreads        (Phase 3)
  quant/       engine, probability, EV, scoring        (Phase 3)
  agents/      analyst, adversarial                    (Phase 4)
  risk/        governor, limits, position_sizing       (Phase 3)
  execution/   validator, executor                     (Phase 5)
  portfolio/   monitor, performance                    (Phase 7)
  journal/     decisions, audit                         (Phase 5/7)
  backtesting/ engine, replay                           (Phase 7)
  api/         routes, websocket, schemas
```

## Phase 1 (current)

Foundation only: centralized config, structured JSON logging, exception
hierarchy, SQLite schema (`decisions`, `audit_log`, `orders`), FastAPI app with
`/api/health`, and the read-only diagnostic command
(`python -m backend.main --diagnostic`). No market or order calls are made.
