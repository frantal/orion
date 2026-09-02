"""Alpaca MCP Adapter — ORION's single boundary to Alpaca.

Every part of ORION that needs Alpaca data goes through :class:`AlpacaAdapter`.
No other module imports :class:`~backend.alpaca.client.AlpacaClient` directly.
The adapter parses raw payloads into typed models, enforces paper trading, and
degrades safely (raising typed errors) so no failure can trigger an unsafe
execution downstream.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from backend.alpaca.client import AlpacaClient
from backend.alpaca.models import (
    Account,
    Clock,
    Greeks,
    OptionChain,
    OptionContract,
    OptionType,
    Position,
    StockQuote,
    StockSnapshot,
)
from backend.core.config import Settings, get_settings
from backend.core.exceptions import AlpacaUnavailableError, InvalidQuoteError
from backend.core.logging import get_logger

logger = get_logger("alpaca.adapter")


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_occ_symbol(symbol: str) -> tuple[str, date, OptionType, float]:
    """Parse an OCC option symbol, e.g. ``SPY260918C00540000``.

    Returns ``(underlying, expiration, option_type, strike)``.
    """
    if len(symbol) < 16:
        raise ValueError(f"Malformed OCC symbol: {symbol}")
    strike = int(symbol[-8:]) / 1000.0
    type_char = symbol[-9].upper()
    yymmdd = symbol[-15:-9]
    underlying = symbol[:-15]
    expiration = datetime.strptime(yymmdd, "%y%m%d").date()
    option_type = OptionType.CALL if type_char == "C" else OptionType.PUT
    return underlying, expiration, option_type, strike


class AlpacaAdapter:
    """High-level, typed access to Alpaca. The only Alpaca boundary in ORION."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        if self._settings.use_alpaca_cli:
            # Route trading/account ops through the Alpaca CLI (lazy import).
            from backend.alpaca.cli_client import AlpacaCLIClient

            self._client = AlpacaCLIClient(self._settings)
        else:
            self._client = AlpacaClient(self._settings)

    @property
    def configured(self) -> bool:
        return self._settings.alpaca_configured

    @property
    def paper_trading(self) -> bool:
        return self._settings.alpaca_paper_trade

    # --- Account & clock ---

    async def get_account(self) -> Account:
        raw = await self._client.get_account()
        return Account(
            account_number=str(raw.get("account_number", "")),
            status=str(raw.get("status", "")),
            currency=str(raw.get("currency", "USD")),
            equity=_to_float(raw.get("equity")) or 0.0,
            cash=_to_float(raw.get("cash")) or 0.0,
            buying_power=_to_float(raw.get("buying_power")) or 0.0,
            portfolio_value=_to_float(raw.get("portfolio_value")) or 0.0,
            options_buying_power=_to_float(raw.get("options_buying_power")),
            options_trading_level=(
                int(raw["options_trading_level"])
                if raw.get("options_trading_level") is not None
                else None
            ),
            pattern_day_trader=bool(raw.get("pattern_day_trader", False)),
            trading_blocked=bool(raw.get("trading_blocked", False)),
        )

    async def get_clock(self) -> Clock:
        raw = await self._client.get_clock()
        return Clock(
            timestamp=raw["timestamp"],
            is_open=bool(raw.get("is_open", False)),
            next_open=raw["next_open"],
            next_close=raw["next_close"],
        )

    # --- Market data ---

    async def get_stock_quote(self, symbol: str) -> StockQuote:
        raw = await self._client.get_latest_stock_quote(symbol)
        quote = raw.get("quote") or {}
        if not quote:
            raise InvalidQuoteError(f"No quote returned for {symbol}")
        return StockQuote(
            symbol=raw.get("symbol", symbol),
            bid=_to_float(quote.get("bp")) or 0.0,
            ask=_to_float(quote.get("ap")) or 0.0,
            bid_size=_to_float(quote.get("bs")) or 0.0,
            ask_size=_to_float(quote.get("as")) or 0.0,
            timestamp=quote.get("t"),
        )

    async def get_market_snapshot(self, symbol: str) -> StockSnapshot:
        raw = await self._client.get_stock_snapshot(symbol)
        latest_trade = raw.get("latestTrade") or {}
        daily = raw.get("dailyBar") or {}
        prev = raw.get("prevDailyBar") or {}
        price = _to_float(latest_trade.get("p")) or _to_float(daily.get("c"))
        if price is None:
            raise InvalidQuoteError(f"No price available for {symbol}")
        return StockSnapshot(
            symbol=symbol,
            price=price,
            prev_close=_to_float(prev.get("c")),
            day_open=_to_float(daily.get("o")),
            day_high=_to_float(daily.get("h")),
            day_low=_to_float(daily.get("l")),
            day_volume=_to_float(daily.get("v")),
        )

    # --- Options ---

    async def get_option_chain(
        self,
        underlying: str,
        expiration_gte: date | None = None,
        expiration_lte: date | None = None,
        strike_gte: float | None = None,
        strike_lte: float | None = None,
    ) -> OptionChain:
        """Fetch and parse an option chain, with optional server-side filters."""
        params: dict[str, Any] = {}
        if expiration_gte:
            params["expiration_date_gte"] = expiration_gte.isoformat()
        if expiration_lte:
            params["expiration_date_lte"] = expiration_lte.isoformat()
        if strike_gte is not None:
            params["strike_price_gte"] = strike_gte
        if strike_lte is not None:
            params["strike_price_lte"] = strike_lte

        raw = await self._client.get_option_snapshots(underlying, params)
        snapshots = raw.get("snapshots") or {}
        contracts: list[OptionContract] = []
        for occ_symbol, snap in snapshots.items():
            contract = self._parse_option_snapshot(occ_symbol, snap)
            if contract is not None:
                contracts.append(contract)
        logger.info(
            "option chain fetched",
            extra={"underlying": underlying, "contracts": len(contracts)},
        )
        return OptionChain(underlying=underlying, contracts=contracts)

    @staticmethod
    def _parse_option_snapshot(occ_symbol: str, snap: dict[str, Any]) -> OptionContract | None:
        try:
            underlying, expiration, option_type, strike = parse_occ_symbol(occ_symbol)
        except ValueError:
            logger.warning("skipping malformed option symbol", extra={"symbol": occ_symbol})
            return None

        quote = snap.get("latestQuote") or {}
        trade = snap.get("latestTrade") or {}
        daily = snap.get("dailyBar") or {}
        greeks_raw = snap.get("greeks") or {}

        return OptionContract(
            symbol=occ_symbol,
            underlying=underlying,
            expiration=expiration,
            strike=strike,
            option_type=option_type,
            bid=_to_float(quote.get("bp")),
            ask=_to_float(quote.get("ap")),
            last=_to_float(trade.get("p")),
            volume=_to_float(daily.get("v")),
            open_interest=_to_float(snap.get("openInterest")),
            implied_volatility=_to_float(snap.get("impliedVolatility")),
            greeks=Greeks(
                delta=_to_float(greeks_raw.get("delta")),
                gamma=_to_float(greeks_raw.get("gamma")),
                theta=_to_float(greeks_raw.get("theta")),
                vega=_to_float(greeks_raw.get("vega")),
                rho=_to_float(greeks_raw.get("rho")),
            ),
        )

    # --- Positions & orders ---

    async def get_positions(self) -> list[Position]:
        raw = await self._client.get_positions()
        positions: list[Position] = []
        for p in raw:
            positions.append(
                Position(
                    symbol=str(p.get("symbol", "")),
                    asset_class=str(p.get("asset_class", "")),
                    qty=_to_float(p.get("qty")) or 0.0,
                    side=str(p.get("side", "")),
                    avg_entry_price=_to_float(p.get("avg_entry_price")),
                    market_value=_to_float(p.get("market_value")),
                    cost_basis=_to_float(p.get("cost_basis")),
                    unrealized_pl=_to_float(p.get("unrealized_pl")),
                )
            )
        return positions

    async def get_orders(self, status: str = "all", limit: int = 50) -> list[dict[str, Any]]:
        return await self._client.get_orders(status=status, limit=limit)

    async def submit_order(self, body: dict[str, Any]) -> dict[str, Any]:
        """Submit an order to Alpaca (paper). Callers build the body via the executor."""
        if not self._settings.alpaca_paper_trade:
            raise AlpacaUnavailableError("Live trading is forbidden.")
        return await self._client.submit_order(body)

    # --- Health ---

    async def health_check(self) -> dict[str, Any]:
        """Read-only connectivity probe. Never places an order.

        Returns a dict of check name -> {ok, detail}. Fetches account, clock,
        SPY quote and a small SPY option chain.
        """
        results: dict[str, Any] = {}

        try:
            account = await self.get_account()
            results["account"] = {
                "ok": True,
                "detail": f"status={account.status} buying_power={account.buying_power:.2f}",
            }
        except AlpacaUnavailableError as exc:
            results["account"] = {"ok": False, "detail": str(exc)}
            return results  # No point continuing if auth/account fails.

        try:
            clock = await self.get_clock()
            results["clock"] = {
                "ok": True,
                "detail": f"market {'OPEN' if clock.is_open else 'CLOSED'}",
            }
        except AlpacaUnavailableError as exc:
            results["clock"] = {"ok": False, "detail": str(exc)}

        try:
            quote = await self.get_stock_quote("SPY")
            results["spy_quote"] = {"ok": True, "detail": f"SPY mid={quote.mid}"}
        except (AlpacaUnavailableError, InvalidQuoteError) as exc:
            results["spy_quote"] = {"ok": False, "detail": str(exc)}

        try:
            chain = await self.get_option_chain("SPY")
            results["spy_options"] = {
                "ok": chain.count > 0,
                "detail": f"{chain.count} contracts",
            }
        except AlpacaUnavailableError as exc:
            results["spy_options"] = {"ok": False, "detail": str(exc)}

        return results


def get_adapter(settings: Settings | None = None) -> AlpacaAdapter:
    """Factory for the Alpaca adapter (or the offline demo adapter)."""
    settings = settings or get_settings()
    if settings.use_demo_data:
        # Lazy import avoids a circular dependency (demo adapter subclasses this).
        from backend.alpaca.demo_adapter import DemoAdapter

        return DemoAdapter(settings)
    return AlpacaAdapter(settings)
