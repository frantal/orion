"""System diagnostics.

Runs a read-only health assessment across ORION's foundational subsystems.
NEVER places an order. Used by ``python -m backend.main --diagnostic`` and by
the ``/api/health`` endpoint.
"""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path

from backend.core.config import Settings, get_settings
from backend.core.database import check_db
from backend.core.logging import get_logger

logger = get_logger("diagnostics")


@dataclass
class Check:
    """A single diagnostic check result."""

    name: str
    ok: bool
    detail: str


@dataclass
class DiagnosticReport:
    """Aggregated diagnostic result."""

    checks: list[Check] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return all(c.ok for c in self.checks)

    def add(self, name: str, ok: bool, detail: str) -> None:
        self.checks.append(Check(name=name, ok=ok, detail=detail))

    def to_dict(self) -> dict[str, object]:
        return {
            "healthy": self.healthy,
            "checks": [
                {"name": c.name, "ok": c.ok, "detail": c.detail} for c in self.checks
            ],
        }


def run_diagnostics(settings: Settings | None = None) -> DiagnosticReport:
    """Execute all foundational checks and return a report. Never trades."""
    settings = settings or get_settings()
    report = DiagnosticReport()

    # Python runtime
    py_ok = sys.version_info >= (3, 10)
    report.add(
        "python",
        py_ok,
        f"{platform.python_version()} ({'ok' if py_ok else 'requires >=3.10'})",
    )

    # Environment
    report.add(
        "environment",
        True,
        f"env={settings.environment} demo_mode={settings.demo_mode}",
    )

    # Database
    db_ok = check_db(settings)
    report.add(
        "database",
        db_ok,
        f"sqlite at {settings.sqlite_path} ({'reachable' if db_ok else 'unreachable'})",
    )

    # Alpaca credentials (presence only — never log the values)
    report.add(
        "alpaca_credentials",
        settings.alpaca_configured or settings.use_demo_data,
        "configured"
        if settings.alpaca_configured
        else ("demo data (no creds needed)" if settings.use_demo_data else "missing (set ALPACA_API_KEY/SECRET)"),
    )

    # Alpaca MCP adapter (live connectivity checked by run_alpaca_diagnostics)
    integration = "Alpaca CLI" if settings.use_alpaca_cli else "REST"
    report.add(
        "alpaca_integration",
        True,
        f"trading via {integration}; market-data via REST — live checks run separately",
    )
    if settings.use_alpaca_cli:
        cli = settings.alpaca_cli_executable
        cli_found = cli == "alpaca" or Path(cli).exists()
        report.add(
            "alpaca_cli",
            cli_found,
            f"binary: {cli}" if cli_found else f"CLI binary not found at {cli}",
        )

    # Paper trading enforcement — this is a safety gate, not just a check.
    paper_ok = settings.alpaca_paper_trade is True
    report.add(
        "paper_trading",
        paper_ok,
        "ENFORCED (paper)" if paper_ok else "DANGER: live trading configured — ORION refuses",
    )

    logger.info("diagnostics complete", extra={"healthy": report.healthy})
    return report


async def run_alpaca_diagnostics(settings: Settings | None = None) -> list[Check]:
    """Run read-only live Alpaca checks (account, clock, SPY quote, chain).

    Returns an empty list when credentials are not configured. Never trades.
    """
    settings = settings or get_settings()
    if not settings.alpaca_configured and not settings.use_demo_data:
        return []

    # Imported lazily so Phase 1 code paths never require the Alpaca layer.
    from backend.alpaca.mcp_adapter import get_adapter
    checks: list[Check] = []
    results = await get_adapter(settings).health_check()
    for name, outcome in results.items():
        checks.append(
            Check(name=f"alpaca_{name}", ok=bool(outcome["ok"]), detail=str(outcome["detail"]))
        )
    return checks

