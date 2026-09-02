# ORION

### Autonomous Options Alpha Agent
**"The agent that has to prove its trade."**

ORION is an autonomous options trading agent built for the Alpaca AI Trading
Agents Hackathon 2026. Unlike agents that go straight from *find* to *trade*,
ORION must **prove every trade** through a disciplined decision pipeline before
anything reaches the (paper) broker.

```
Find → Quantify → Explain → Attack → Risk Check → Validate → EXECUTE / NO TRADE
```

`NO TRADE` is a first-class, valued outcome. ORION optimizes **decision
quality**, not trade count.

---

## Why ORION is different

- **Hybrid intelligence.** Deterministic Python does all pricing, Greeks,
  probability, scoring, position sizing and risk. The LLM only *reasons* —
  thesis, explanation, adversarial critique. Financial math never depends on
  the LLM.
- **Adversarial layer.** Every opportunity is attacked by an Adversarial Agent
  that tries to prove the trade wrong before it can proceed.
- **Independent Risk Governor.** A deterministic gate that can **veto** any
  decision — including the LLM's — for exposure, liquidity, spread, scores or
  limits.
- **Auditable.** Every decision produces an audit log and a searchable journal.

---

## Safety (non-negotiable)

- **Paper trading only.** Default `ALPACA_PAPER_TRADE=true`; ORION refuses to
  run against live money.
- **No secrets in code.** Credentials come from the environment / `.env`
  (gitignored). Nothing sensitive is logged or sent to the frontend.
- **No unsafe automatic execution.** On any error or ambiguity → `NO TRADE`.

---

## Getting started

```powershell
# 1. Create a virtual environment and install dependencies
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Configure environment
Copy-Item .env.example .env
# edit .env and add your Alpaca PAPER keys (keep ALPACA_PAPER_TRADE=true)

# 3. Run diagnostics (read-only, never trades)
python -m backend.main --diagnostic

# 4. Run the API server
python -m backend.main
# Health: http://127.0.0.1:8000/api/health
# Docs:   http://127.0.0.1:8000/docs
```

Run the tests:

```powershell
pytest
```

### Dashboard (frontend)

```powershell
cd frontend
npm install
npm run dev
# open http://localhost:5173  (proxies /api to the backend on :8000)
```

The dashboard is a dark, quant-styled cockpit centred on the **Decision Engine**:
market regime, the scan pipeline (Market → Opportunity → Quant → AI Thesis →
Adversarial → Risk → Decision → Execution), ranked opportunities, AI thesis vs.
adversarial challenge, Risk Governor verdict, execution preview and portfolio.

### Offline demo (no credentials)

Set `USE_DEMO_DATA=true` in `.env` to run ORION against a deterministic synthetic
market — no Alpaca keys, no network. See [`docs/DEMO.md`](docs/DEMO.md).

```powershell
python -m scripts.seed_demo   # optional: pre-populate the journals
```

---

## Architecture (high level)

```
Market Data → Market Intelligence → Options Scanner → Quant Engine
   → Alpha Engine (AI Analyst) → Adversarial Agent → Risk Governor
   → Trade Validator → Execution Engine → Alpaca Paper Trading
   → Portfolio Monitor → Performance → Decision Journal
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and
[`docs/DECISION_ENGINE.md`](docs/DECISION_ENGINE.md) for detail.

---

## Development status

Built incrementally in phases:

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Foundation: config, logging, DB, FastAPI health, diagnostics, tests | ✅ Done |
| 2 | Alpaca MCP adapter, account, market data, options chain | ✅ Done |
| 3 | Options Scanner, Quant Engine, Risk Engine | ✅ Done |
| 4 | AI Analyst, Adversarial Agent | ✅ Done |
| 5 | Decision Engine, Trade Validator, Paper Execution | ✅ Done |
| 6 | Dashboard (React/Vite) | ✅ Done |
| 7 | Backtesting, Decision Journal, Performance | ✅ Done |
| 8 | Demo mode, testing, polish | ✅ Done |

---

## License

MIT — see [`LICENSE`](LICENSE).
