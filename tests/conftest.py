"""Shared pytest fixtures for ORION."""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

import pytest

from backend.alpaca.models import Greeks, OptionContract, OptionType
from backend.core.config import Settings


@pytest.fixture()
def tmp_settings(tmp_path: Path) -> Settings:
    """Settings pointing at an isolated temporary SQLite database."""
    db_path = tmp_path / "test_orion.db"
    return Settings(
        ALPACA_API_KEY="",
        ALPACA_SECRET_KEY="",
        ALPACA_PAPER_TRADE=True,
        DEMO_MODE=True,
        DATABASE_URL=f"sqlite:///{db_path.as_posix()}",
    )


def make_contract(
    strike: float,
    option_type: OptionType,
    *,
    bid: float,
    ask: float,
    underlying: str = "SPY",
    dte: int = 30,
    volume: float | None = 100.0,
    open_interest: float | None = 500.0,
    iv: float | None = 0.20,
    delta: float | None = 0.5,
) -> OptionContract:
    """Build an OptionContract for tests."""
    expiration = date.today() + timedelta(days=dte)
    return OptionContract(
        symbol=f"{underlying}TEST{int(strike)}",
        underlying=underlying,
        expiration=expiration,
        strike=strike,
        option_type=option_type,
        bid=bid,
        ask=ask,
        last=round((bid + ask) / 2, 2),
        volume=volume,
        open_interest=open_interest,
        implied_volatility=iv,
        greeks=Greeks(delta=delta),
    )


@pytest.fixture()
def contract_factory():
    return make_contract

