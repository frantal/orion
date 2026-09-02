# ORION — Strategy

## Objective

Identify options opportunities with genuine alpha potential, quantify them,
attack them, risk-check them, and only then execute (on paper) — or record a
disciplined **NO TRADE**.

## Supported strategies (Phase 3, risk-defined first)

1. Long Call
2. Long Put
3. Bull Call Spread
4. Bear Put Spread
5. Bull Put Spread
6. Bear Call Spread

Defined-risk strategies are prioritized so maximum loss is always known.

## Market regimes

The Market Intelligence module classifies the regime deterministically:

`BULLISH · BEARISH · NEUTRAL · HIGH_VOLATILITY · LOW_VOLATILITY · EVENT_DRIVEN · UNCERTAIN`

Strategy selection is aligned to regime (e.g. debit spreads in trending
regimes, credit spreads when IV is rich).

## Alpha Score (0–100)

| Weight | Component |
|--------|-----------|
| 30% | Expected value |
| 20% | Risk/reward |
| 15% | Liquidity |
| 15% | Volatility edge |
| 10% | Market regime alignment |
| 10% | Catalyst / evidence |

A separate **Risk Score (0–100)** captures relative risk (0 = low, 100 = high).

## Filtering discipline

Quantitative filters run **before** any LLM call:

```
RAW DATA → FILTER → QUANT → TOP CANDIDATES → LLM
```

This keeps the generative layer cheap, focused, and safe.
