"""Tests for diagnostics and the health endpoint."""

from __future__ import annotations

import httpx
import pytest

from backend.core.database import init_db
from backend.core.diagnostics import run_diagnostics


def test_diagnostics_report_shape(tmp_settings) -> None:
    init_db(tmp_settings)
    report = run_diagnostics(tmp_settings)
    names = {c.name for c in report.checks}
    assert {
        "python",
        "environment",
        "database",
        "alpaca_credentials",
        "paper_trading",
    } <= names


def test_paper_trading_check_passes_by_default(tmp_settings) -> None:
    init_db(tmp_settings)
    report = run_diagnostics(tmp_settings)
    paper = next(c for c in report.checks if c.name == "paper_trading")
    assert paper.ok is True


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    from backend.app import create_app

    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["paper_trading"] is True
    assert "checks" in body
