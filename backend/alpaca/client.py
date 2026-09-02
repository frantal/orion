"""Low-level async HTTP client for the Alpaca REST API.

This is the *only* place that performs raw HTTP against Alpaca. It handles
authentication, timeouts, and error mapping, returning plain ``dict`` payloads.
Higher-level parsing and domain logic live in
:mod:`backend.alpaca.mcp_adapter`.
"""

from __future__ import annotations

from typing import Any

import httpx

from backend.core.config import Settings, get_settings
from backend.core.exceptions import AlpacaUnavailableError
from backend.core.logging import get_logger

logger = get_logger("alpaca.client")


class AlpacaClient:
    """Thin async wrapper over Alpaca's trading and market-data REST APIs."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self._settings.alpaca_api_key,
            "APCA-API-SECRET-KEY": self._settings.alpaca_secret_key,
            "accept": "application/json",
        }

    async def _get(self, base_url: str, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._settings.alpaca_configured:
            raise AlpacaUnavailableError("Alpaca credentials are not configured.")
        url = f"{base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._settings.alpaca_timeout_seconds) as client:
                resp = await client.get(url, headers=self._headers, params=params)
        except httpx.HTTPError as exc:
            logger.error("alpaca request failed", extra={"path": path, "error": str(exc)})
            raise AlpacaUnavailableError(f"Alpaca request failed: {exc}") from exc

        if resp.status_code == 401:
            raise AlpacaUnavailableError("Alpaca authentication failed (401). Check API keys.")
        if resp.status_code == 429:
            raise AlpacaUnavailableError("Alpaca rate limit exceeded (429).")
        if resp.status_code >= 400:
            raise AlpacaUnavailableError(
                f"Alpaca error {resp.status_code} on {path}: {resp.text[:200]}"
            )
        try:
            return resp.json()
        except ValueError as exc:
            raise AlpacaUnavailableError(f"Invalid JSON from Alpaca on {path}") from exc

    async def _post(self, base_url: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        if not self._settings.alpaca_configured:
            raise AlpacaUnavailableError("Alpaca credentials are not configured.")
        url = f"{base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._settings.alpaca_timeout_seconds) as client:
                resp = await client.post(url, headers=self._headers, json=body)
        except httpx.HTTPError as exc:
            logger.error("alpaca post failed", extra={"path": path, "error": str(exc)})
            raise AlpacaUnavailableError(f"Alpaca request failed: {exc}") from exc

        if resp.status_code == 401:
            raise AlpacaUnavailableError("Alpaca authentication failed (401). Check API keys.")
        if resp.status_code == 429:
            raise AlpacaUnavailableError("Alpaca rate limit exceeded (429).")
        if resp.status_code >= 400:
            raise AlpacaUnavailableError(
                f"Alpaca error {resp.status_code} on {path}: {resp.text[:300]}"
            )
        try:
            return resp.json()
        except ValueError as exc:
            raise AlpacaUnavailableError(f"Invalid JSON from Alpaca on {path}") from exc

    # --- Trading API (paper) ---

    async def get_account(self) -> dict[str, Any]:
        return await self._get(self._settings.alpaca_trading_base_url, "/v2/account")

    async def get_clock(self) -> dict[str, Any]:
        return await self._get(self._settings.alpaca_trading_base_url, "/v2/clock")

    async def get_positions(self) -> list[dict[str, Any]]:
        data = await self._get(self._settings.alpaca_trading_base_url, "/v2/positions")
        return data if isinstance(data, list) else []

    async def get_orders(self, status: str = "all", limit: int = 50) -> list[dict[str, Any]]:
        data = await self._get(
            self._settings.alpaca_trading_base_url,
            "/v2/orders",
            params={"status": status, "limit": limit, "nested": "true"},
        )
        return data if isinstance(data, list) else []

    async def submit_order(self, body: dict[str, Any]) -> dict[str, Any]:
        return await self._post(self._settings.alpaca_trading_base_url, "/v2/orders", body)

    # --- Market Data API ---

    async def get_latest_stock_quote(self, symbol: str) -> dict[str, Any]:
        return await self._get(
            self._settings.alpaca_data_base_url, f"/v2/stocks/{symbol}/quotes/latest"
        )

    async def get_stock_snapshot(self, symbol: str) -> dict[str, Any]:
        return await self._get(
            self._settings.alpaca_data_base_url, f"/v2/stocks/{symbol}/snapshot"
        )

    async def get_option_snapshots(
        self, underlying: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        query = {"feed": self._settings.alpaca_options_feed, "limit": 1000}
        if params:
            query.update(params)
        return await self._get(
            self._settings.alpaca_data_base_url,
            f"/v1beta1/options/snapshots/{underlying}",
            params=query,
        )
