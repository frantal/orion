"""ORION entrypoint.

Usage:
    python -m backend.main                 # run the API server
    python -m backend.main --diagnostic    # run read-only diagnostics (no trading)
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from backend.core.config import get_settings
from backend.core.database import init_db
from backend.core.diagnostics import run_alpaca_diagnostics, run_diagnostics
from backend.core.logging import configure_logging


def _print_diagnostics() -> int:
    """Run diagnostics and print a human-readable report. Returns exit code."""
    settings = get_settings()
    configure_logging(settings.log_level)
    init_db(settings)
    report = run_diagnostics(settings)

    # Live Alpaca checks (read-only) when credentials are present.
    if settings.alpaca_configured or settings.use_demo_data:
        try:
            for check in asyncio.run(run_alpaca_diagnostics(settings)):
                report.checks.append(check)
        except Exception as exc:  # noqa: BLE001 - diagnostics must never crash
            report.add("alpaca_live", False, f"live check error: {exc}")

    print("\n" + "=" * 52)
    print("  ORION DIAGNOSTIC")
    print("=" * 52)
    for check in report.checks:
        mark = "PASS" if check.ok else "FAIL"
        print(f"  [{mark}] {check.name:<20} {check.detail}")
    print("-" * 52)
    print(f"  OVERALL: {'HEALTHY' if report.healthy else 'DEGRADED'}")
    print(f"  Paper trading: {'ENFORCED' if settings.alpaca_paper_trade else 'OFF (UNSAFE)'}")
    print("=" * 52 + "\n")
    return 0 if report.healthy else 1


def _run_server() -> int:
    """Run the uvicorn server."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "backend.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="orion", description="ORION agent")
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="Run read-only diagnostics and exit (never trades).",
    )
    args = parser.parse_args(argv)

    if args.diagnostic:
        return _print_diagnostics()
    return _run_server()


if __name__ == "__main__":
    sys.exit(main())
