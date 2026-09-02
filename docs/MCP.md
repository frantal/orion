# ORION — Alpaca Integration (CLI + REST)

ORION integrates with Alpaca for account data, market data, options data and
(paper) trading. To satisfy the hackathon's *"utilize the MCP server or CLI
tools"* requirement, ORION routes its **trading and account operations through
the official Alpaca CLI**, while market data uses the REST market-data API.

## Two integration modes

| Concern | Default (REST) | `USE_ALPACA_CLI=true` |
|---------|----------------|------------------------|
| Account, clock, positions, orders, **order submission** | REST | **Alpaca CLI** (`alpaca api ...`) |
| Stock quotes, snapshots, option chains/Greeks/IV | REST | REST |

Everything is abstracted behind a single boundary — `backend/alpaca/mcp_adapter.py`
(`AlpacaAdapter`). It picks `AlpacaCLIClient` or `AlpacaClient` based on
configuration; no other module talks to Alpaca directly.

## Installing the Alpaca CLI

The CLI is a single Go binary. Any of:

```powershell
# Prebuilt release (Windows) — bundled into tools/ in this repo
# https://github.com/alpacahq/cli/releases

# or via Go
go install github.com/alpacahq/cli/cmd/alpaca@latest

# or Homebrew (macOS/Linux)
brew install alpacahq/tap/cli
```

ORION auto-detects `tools/alpaca(.exe)` or an `alpaca` binary on `PATH`. Override
with `ALPACA_CLI_PATH` in `.env`.

## Configuration

```
ALPACA_API_KEY=...        # PAPER key
ALPACA_SECRET_KEY=...      # PAPER secret
ALPACA_PAPER_TRADE=true    # never set to false
USE_ALPACA_CLI=true        # route trading/account through the CLI
```

The CLI is invoked non-interactively with credentials passed via environment,
`ALPACA_QUIET=1`, and `ALPACA_LIVE_TRADE=false` — paper is always enforced. The
CLI returns JSON on stdout; errors are JSON on stderr (exit code 2 = auth).

## How ORION uses the CLI

`backend/alpaca/cli_client.py` shells out to the CLI's raw API command, e.g.:

```
alpaca api GET  /v2/account
alpaca api GET  /v2/clock
alpaca api GET  /v2/positions
alpaca api GET  /v2/orders  --query "status=all&limit=50&nested=true"
alpaca api POST /v2/orders  --body '{ ...order... }'   # single-leg & multi-leg spreads
```

## Capabilities used

- **account** — equity, buying power, positions, options level
- **stock-data** — quotes, bars, snapshots (REST)
- **options-data** — option chains, quotes, Greeks, IV, snapshots (REST)
- **trading** — paper order submission (single-leg `simple` and multi-leg `mleg`)

## Verification (read-only, no orders)

`python -m backend.main --diagnostic` confirms: CLI binary found, account, market
clock, SPY quote and SPY option chain. If any check fails, MCP/CLI-dependent work
halts until it is diagnosed and fixed.
