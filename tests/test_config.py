"""Tests for configuration and paper-trading safety enforcement."""

from __future__ import annotations

from backend.core.config import Settings


def test_defaults_are_safe() -> None:
    # _env_file=None isolates the test from any ambient .env so we assert defaults.
    s = Settings(_env_file=None, ALPACA_API_KEY="", ALPACA_SECRET_KEY="")
    assert s.alpaca_paper_trade is True
    assert s.demo_mode is True


def test_alpaca_configured_flag() -> None:
    assert Settings(ALPACA_API_KEY="k", ALPACA_SECRET_KEY="s").alpaca_configured is True
    assert Settings(ALPACA_API_KEY="", ALPACA_SECRET_KEY="s").alpaca_configured is False


def test_paper_trade_can_be_set_but_defaults_true() -> None:
    # A user could technically set it, but ORION's default posture is paper.
    assert Settings(_env_file=None).alpaca_paper_trade is True


def test_sqlite_path_resolves_relative(tmp_settings) -> None:
    assert str(tmp_settings.sqlite_path).endswith("test_orion.db")
