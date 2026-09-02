"""Alpaca CLI-backed client.

Routes account/clock/positions/orders and order submission through the official
Alpaca CLI (``alpaca api ...``, JSON on stdout), satisfying the hackathon's
"utilize the MCP server or CLI tools" requirement. Market-data reads are
inherited from :class:`AlpacaClient` (REST), because the CLI's raw ``api``
command targets the trading base URL only.

Paper trading is enforced: the CLI defaults to paper and we never set
``ALPACA_LIVE_TRADE``.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from backend.alpaca.client import AlpacaClient
from backend.core.config import Settings, get_settings
from backend.core.exceptions import AlpacaUnavailableError
from backend.core.logging import get_logger

logger = get_logger("alpaca.cli")


class AlpacaCLIClient(AlpacaClient):
    """Trading operations via the Alpaca CLI; market data via inherited REST."""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(settings or get_settings())

    def _env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["ALPACA_API_KEY"] = self._settings.alpaca_api_key
        env["ALPACA_SECRET_KEY"] = self._settings.alpaca_secret_key
        env["ALPACA_QUIET"] = "1"
        # Paper is the CLI default; make the intent explicit and never go live.
        env["ALPACA_LIVE_TRADE"] = "false"
        env.pop("ALPACA_PROFILE", None)
        return env

    async def _run(self, *args: str) -> str:
        if not self._settings.alpaca_configured:
            raise AlpacaUnavailableError("Alpaca credentials are not configured.")
        cli = self._settings.alpaca_cli_executable
        try:
            proc = await asyncio.create_subprocess_exec(
                cli, *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._env(),
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self._settings.alpaca_timeout_seconds + 20
            )
        except FileNotFoundError as exc:
            raise AlpacaUnavailableError(f"Alpaca CLI not found at '{cli}'.") from exc
        except (asyncio.TimeoutError, OSError) as exc:
            raise AlpacaUnavailableError(f"Alpaca CLI call failed: {exc}") from exc

        if proc.returncode != 0:
            detail = stderr.decode(errors="replace").strip() or stdout.decode(errors="replace").strip()
            if proc.returncode == 2:
                raise AlpacaUnavailableError(f"Alpaca CLI auth error: {detail[:200]}")
            raise AlpacaUnavailableError(f"Alpaca CLI error ({proc.returncode}): {detail[:200]}")
        return stdout.decode(errors="replace")

    async def _api(self, method: str, path: str, *, query: str | None = None, body: dict | None = None) -> Any:
        args = ["api", method, path]
        if query:
            args += ["--query", query]
        if body is not None:
            args += ["--body", json.dumps(body)]
        out = await self._run(*args)
        try:
            return json.loads(out) if out.strip() else {}
        except ValueError as exc:
            raise AlpacaUnavailableError("Alpaca CLI returned non-JSON output") from exc

    # --- Trading API (via CLI) ---

    async def get_account(self) -> dict[str, Any]:
        return await self._api("GET", "/v2/account")

    async def get_clock(self) -> dict[str, Any]:
        return await self._api("GET", "/v2/clock")

    async def get_positions(self) -> list[dict[str, Any]]:
        data = await self._api("GET", "/v2/positions")
        return data if isinstance(data, list) else []

    async def get_orders(self, status: str = "all", limit: int = 50) -> list[dict[str, Any]]:
        data = await self._api(
            "GET", "/v2/orders", query=f"status={status}&limit={limit}&nested=true"
        )
        return data if isinstance(data, list) else []

    async def submit_order(self, body: dict[str, Any]) -> dict[str, Any]:
        logger.info("submitting order via Alpaca CLI", extra={"symbol": body.get("symbol")})
        return await self._api("POST", "/v2/orders", body=body)
