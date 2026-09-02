# ORION — Demo Guide

ORION ships with a fully **offline demo mode** so it can be evaluated with **no
Alpaca credentials and no network** — ideal for judging. The demo never contacts
a broker and never places a real order.

---

## 1. Run the demo (no credentials required)

```powershell
# Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env
# In .env set:
#   USE_DEMO_DATA=true
#   DEMO_MODE=true
# (Alpaca keys can stay empty.)

# Seed the journals with a controlled run (optional but recommended)
python -m scripts.seed_demo

# Start the API
python -m backend.main
```

```powershell
# Frontend (separate terminal)
cd frontend
npm install
npm run dev
# open http://localhost:5173
```

Click **SCAN**. ORION runs the full pipeline on a deterministic synthetic market
(a Black-Scholes-priced SPY option chain in a mildly **bullish** regime).

---

## 2. What the demo shows

The dashboard is built around the **Decision Engine**. In one screen you see:

```
MARKET → OPPORTUNITY → QUANT → AI THESIS → ADVERSARIAL → RISK → DECISION → EXECUTION
```

- **Market Regime** — deterministic classifier (BULLISH in the demo).
- **Opportunities** — ranked by Alpha Score, each with its Risk Governor verdict.
- **Top Opportunity** — Alpha / Risk / Liquidity / Probability-of-Profit, EV, R:R.
- **AI Thesis vs. Adversarial Challenge** — the generative layer (deterministic
  fallback when no LLM is configured); the adversarial agent can reduce the
  Alpha Score.
- **Risk Governor** — independent, deterministic PASS / VETO.
- **Final Decision** — **EXECUTE** or **NO TRADE**, with an execution preview.
- **Backtest (Simulated)** — Monte-Carlo expectancy / win-rate over the top
  opportunities (clearly labelled: simulation, not a guarantee).

The demo intentionally surfaces **both** outcomes: some clean `EXECUTE`s and
several `NO TRADE`s — because ORION optimizes *decision quality*, not trade count.

---

## 3. The differentiator

Most agents go **Find → Trade**. ORION goes:

```
Find → Quantify → Explain → Attack → Risk Check → Validate → EXECUTE / NO TRADE
```

Watch the pipeline: an opportunity can pass the **Risk Governor** yet still be
turned into **NO TRADE** because the **Adversarial Agent** rejected it. That is
the whole thesis — *"the agent that has to prove its trade."*

---

## 4. Live (paper) mode

To run against real Alpaca **paper** data instead of the synthetic market:

```
USE_DEMO_DATA=false
ALPACA_API_KEY=...        # paper key
ALPACA_SECRET_KEY=...      # paper secret
ALPACA_PAPER_TRADE=true    # never set to false
DEMO_MODE=true             # keep true to simulate fills without submitting
```

Set `DEMO_MODE=false` only when you explicitly want to submit **paper** orders to
Alpaca. ORION never trades live money and refuses to start with
`ALPACA_PAPER_TRADE=false`.

---

## 5. Safety

- Paper trading only; live trading is refused.
- No secrets in code, logs, or the frontend (`.env` is gitignored).
- Every decision is audited and journaled.
- On any error or ambiguity, ORION resolves to **NO TRADE**.
