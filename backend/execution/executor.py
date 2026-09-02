"""Execution Engine — paper order submission with duplicate protection.

The client_order_id is derived deterministically from the opportunity id, so a
retry can never create a second order (enforced by a UNIQUE constraint). In
DEMO_MODE the order is simulated and NO network call is made. Otherwise the
order is submitted to Alpaca *paper* and the result is confirmed from the API
response — ORION never assumes a fill.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from backend.alpaca.mcp_adapter import AlpacaAdapter, get_adapter
from backend.core.config import Settings, get_settings
from backend.core.database import get_connection
from backend.core.exceptions import AlpacaUnavailableError
from backend.core.logging import get_logger
from backend.execution.models import (
    ExecutionStatus,
    FinalDecision,
    OrderLeg,
    OrderRequest,
    OrderResult,
)
from backend.execution.validator import client_order_id_for
from backend.journal.audit import AuditLogger
from backend.options.models import Action
from backend.quant.models import Opportunity

logger = get_logger("execution.executor")


class ExecutionEngine:
    def __init__(
        self,
        adapter: AlpacaAdapter | None = None,
        settings: Settings | None = None,
        audit: AuditLogger | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._adapter = adapter or get_adapter(self._settings)
        self._audit = audit or AuditLogger(self._settings)

    def build_order(self, opportunity: Opportunity, decision: FinalDecision) -> OrderRequest:
        cand = opportunity.candidate
        legs = [
            OrderLeg(
                symbol=leg.contract.symbol,
                side=leg.action.value,
                ratio_qty=leg.ratio,
                position_intent="buy_to_open" if leg.action is Action.BUY else "sell_to_open",
            )
            for leg in cand.legs
        ]
        return OrderRequest(
            client_order_id=client_order_id_for(opportunity),
            symbol=opportunity.symbol,
            strategy=opportunity.strategy,
            contracts=decision.preview.contracts,
            limit_price=round(abs(cand.net_premium), 2),
            is_debit=cand.is_debit,
            legs=legs,
        )

    async def execute(self, opportunity: Opportunity, decision: FinalDecision) -> OrderResult:
        order = self.build_order(opportunity, decision)

        # Deterministic duplicate protection via UNIQUE client_order_id.
        if not self._reserve(order):
            self._audit.log("EXECUTION", "duplicate", input_data={"coid": order.client_order_id})
            return OrderResult(
                client_order_id=order.client_order_id,
                status=ExecutionStatus.REJECTED,
                detail="Duplicate order suppressed (client_order_id already exists).",
            )

        if self._settings.demo_mode:
            return self._simulate(order)
        return await self._submit(order)

    def _reserve(self, order: OrderRequest) -> bool:
        """Insert a pending order row. Returns False if it already exists."""
        try:
            with get_connection(self._settings) as conn:
                conn.execute(
                    "INSERT INTO orders (created_at, client_order_id, symbol, strategy, status, payload) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        datetime.now(timezone.utc).isoformat(),
                        order.client_order_id,
                        order.symbol,
                        order.strategy,
                        "pending",
                        order.model_dump_json(),
                    ),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def _update_order(self, coid: str, status: str, broker_id: str | None) -> None:
        with get_connection(self._settings) as conn:
            conn.execute(
                "UPDATE orders SET status = ?, broker_order_id = ? WHERE client_order_id = ?",
                (status, broker_id, coid),
            )

    def _simulate(self, order: OrderRequest) -> OrderResult:
        broker_id = f"sim-{order.client_order_id}"
        self._update_order(order.client_order_id, ExecutionStatus.PAPER_SIMULATED.value, broker_id)
        self._audit.log("EXECUTION", "paper_simulated", output_data={"coid": order.client_order_id})
        logger.info("paper order simulated", extra={"coid": order.client_order_id})
        return OrderResult(
            client_order_id=order.client_order_id,
            status=ExecutionStatus.PAPER_SIMULATED,
            broker_order_id=broker_id,
            detail="DEMO_MODE: order simulated, no broker call.",
        )

    async def _submit(self, order: OrderRequest) -> OrderResult:
        body = self._alpaca_body(order)
        try:
            resp = await self._adapter.submit_order(body)
        except AlpacaUnavailableError as exc:
            self._update_order(order.client_order_id, ExecutionStatus.ERROR.value, None)
            self._audit.log("EXECUTION", "error", error=str(exc))
            return OrderResult(
                client_order_id=order.client_order_id,
                status=ExecutionStatus.ERROR,
                detail=str(exc),
            )

        broker_id = str(resp.get("id")) if resp.get("id") else None
        broker_status = str(resp.get("status", "submitted"))
        self._update_order(order.client_order_id, ExecutionStatus.PAPER_SUBMITTED.value, broker_id)
        self._audit.log(
            "EXECUTION", "paper_submitted", output_data={"broker_id": broker_id, "status": broker_status}
        )
        logger.info("paper order submitted", extra={"coid": order.client_order_id, "broker_id": broker_id})
        return OrderResult(
            client_order_id=order.client_order_id,
            status=ExecutionStatus.PAPER_SUBMITTED,
            broker_order_id=broker_id,
            detail=f"Alpaca status: {broker_status}",
        )

    def _alpaca_body(self, order: OrderRequest) -> dict:
        base = {
            "type": "limit",
            "time_in_force": "day",
            "qty": str(order.contracts),
            "limit_price": str(order.limit_price),
            "client_order_id": order.client_order_id,
        }
        if len(order.legs) == 1:
            leg = order.legs[0]
            base.update({"symbol": leg.symbol, "side": leg.side, "order_class": "simple"})
        else:
            base.update(
                {
                    "order_class": "mleg",
                    "legs": [
                        {
                            "symbol": leg.symbol,
                            "side": leg.side,
                            "ratio_qty": str(leg.ratio_qty),
                            "position_intent": leg.position_intent,
                        }
                        for leg in order.legs
                    ],
                }
            )
        return base
