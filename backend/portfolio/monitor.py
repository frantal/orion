"""Portfolio Monitor — aggregates account state and open exposure."""

from __future__ import annotations

from pydantic import BaseModel

from backend.alpaca.mcp_adapter import AlpacaAdapter
from backend.core.logging import get_logger

logger = get_logger("portfolio.monitor")


class PortfolioSnapshot(BaseModel):
    equity: float
    buying_power: float
    cash: float
    open_positions: int
    open_unrealized_pl: float
    open_exposure: float  # sum of |cost basis| across positions


class PortfolioMonitor:
    def __init__(self, adapter: AlpacaAdapter) -> None:
        self._adapter = adapter

    async def snapshot(self) -> PortfolioSnapshot:
        account = await self._adapter.get_account()
        positions = await self._adapter.get_positions()
        unrealized = sum(p.unrealized_pl or 0.0 for p in positions)
        exposure = sum(abs(p.cost_basis or 0.0) for p in positions)
        return PortfolioSnapshot(
            equity=account.equity,
            buying_power=account.buying_power,
            cash=account.cash,
            open_positions=len(positions),
            open_unrealized_pl=round(unrealized, 2),
            open_exposure=round(exposure, 2),
        )
