"""Centralized application configuration.

All configuration flows through :class:`Settings`. Nothing else in the codebase
should read environment variables directly. Secrets are loaded from the
environment / a local ``.env`` file and are never hard-coded.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.core.exceptions import ConfigurationError

# Project root = two levels up from this file (backend/core/config.py -> repo root).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Runtime configuration for ORION.

    Values are sourced from environment variables (or a local ``.env`` file).
    Field names are case-insensitive.
    """

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Alpaca ---
    alpaca_api_key: str = Field(default="", alias="ALPACA_API_KEY")
    alpaca_secret_key: str = Field(default="", alias="ALPACA_SECRET_KEY")
    alpaca_paper_trade: bool = Field(default=True, alias="ALPACA_PAPER_TRADE")
    alpaca_data_base_url: str = Field(
        default="https://data.alpaca.markets", alias="ALPACA_DATA_BASE_URL"
    )
    alpaca_paper_base_url: str = Field(
        default="https://paper-api.alpaca.markets", alias="ALPACA_PAPER_BASE_URL"
    )
    alpaca_options_feed: str = Field(default="indicative", alias="ALPACA_OPTIONS_FEED")
    alpaca_timeout_seconds: float = Field(default=10.0, alias="ALPACA_TIMEOUT_SECONDS")
    # Route trading/account operations through the official Alpaca CLI instead of REST.
    use_alpaca_cli: bool = Field(default=False, alias="USE_ALPACA_CLI")
    alpaca_cli_path: str = Field(default="", alias="ALPACA_CLI_PATH")

    # --- LLM (optional, generative layer only) ---
    llm_provider: str = Field(default="", alias="LLM_PROVIDER")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="", alias="LLM_MODEL")
    llm_base_url: str = Field(default="https://api.openai.com/v1", alias="LLM_BASE_URL")
    llm_timeout_seconds: float = Field(default=30.0, alias="LLM_TIMEOUT_SECONDS")
    llm_max_tokens: int = Field(default=900, alias="LLM_MAX_TOKENS")
    llm_temperature: float = Field(default=0.4, alias="LLM_TEMPERATURE")

    # --- Runtime ---
    demo_mode: bool = Field(default=True, alias="DEMO_MODE")
    use_demo_data: bool = Field(default=False, alias="USE_DEMO_DATA")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    environment: str = Field(default="development", alias="ENVIRONMENT")

    # --- Server ---
    host: str = Field(default="127.0.0.1", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # --- Database ---
    database_url: str = Field(default="sqlite:///data/orion.db", alias="DATABASE_URL")

    @property
    def alpaca_configured(self) -> bool:
        """True when both Alpaca credentials are present."""
        return bool(self.alpaca_api_key and self.alpaca_secret_key)

    @property
    def alpaca_trading_base_url(self) -> str:
        """Trading API base URL. Always paper while paper trading is enforced."""
        if not self.alpaca_paper_trade:
            # ORION refuses live trading. Callers must keep paper mode on.
            raise ConfigurationError("Live trading is not permitted. Keep ALPACA_PAPER_TRADE=true.")
        return self.alpaca_paper_base_url

    @property
    def alpaca_cli_executable(self) -> str:
        """Resolve the Alpaca CLI binary path (explicit, bundled, or on PATH)."""
        if self.alpaca_cli_path:
            return self.alpaca_cli_path
        bundled = PROJECT_ROOT / "tools" / ("alpaca.exe" if os.name == "nt" else "alpaca")
        return str(bundled) if bundled.exists() else "alpaca"

    @property
    def llm_configured(self) -> bool:
        """True when an LLM provider and key are configured."""
        return bool(self.llm_provider and self.llm_api_key)

    @property
    def sqlite_path(self) -> Path:
        """Filesystem path for the SQLite database, resolved against the project root."""
        url = self.database_url
        prefix = "sqlite:///"
        raw = url[len(prefix):] if url.startswith(prefix) else url
        path = Path(raw)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
