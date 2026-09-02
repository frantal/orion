"""Decision journal — persists every FinalDecision (section 20)."""

from __future__ import annotations

from typing import Any

from backend.core.config import Settings, get_settings
from backend.core.database import get_connection
from backend.core.logging import get_logger
from backend.execution.models import FinalDecision

logger = get_logger("journal.decisions")


class DecisionJournal:
    """Searchable history of ORION's decisions."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def save(self, decision: FinalDecision) -> int:
        """Persist a decision; returns the row id."""
        with get_connection(self._settings) as conn:
            cur = conn.execute(
                """
                INSERT INTO decisions (
                    created_at, symbol, strategy, market_regime, thesis, counter_thesis,
                    alpha_score, risk_score, liquidity_score, expected_value, risk_reward,
                    decision, reason, risk_governor, execution_status, order_id, result, pnl
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.timestamp.isoformat(),
                    decision.symbol,
                    decision.strategy,
                    decision.market_regime,
                    decision.thesis,
                    decision.counter_thesis,
                    decision.alpha_score,
                    decision.risk_score,
                    decision.liquidity_score,
                    decision.expected_value,
                    decision.risk_reward,
                    decision.decision.value,
                    decision.reason,
                    decision.risk_governor,
                    decision.execution_status.value,
                    decision.order_id,
                    None,
                    None,
                ),
            )
            row_id = cur.lastrowid
        logger.info("decision saved", extra={"symbol": decision.symbol, "row_id": row_id})
        return int(row_id) if row_id is not None else -1

    def update_execution(self, row_id: int, execution_status: str, order_id: str | None) -> None:
        with get_connection(self._settings) as conn:
            conn.execute(
                "UPDATE decisions SET execution_status = ?, order_id = ? WHERE id = ?",
                (execution_status, order_id, row_id),
            )

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        with get_connection(self._settings) as conn:
            rows = conn.execute(
                "SELECT * FROM decisions ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def search(
        self,
        symbol: str | None = None,
        decision: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Filter the decision history by symbol and/or decision outcome."""
        clauses: list[str] = []
        params: list[Any] = []
        if symbol:
            clauses.append("symbol = ?")
            params.append(symbol.upper())
        if decision:
            clauses.append("decision = ?")
            params.append(decision.upper())
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with get_connection(self._settings) as conn:
            rows = conn.execute(
                f"SELECT * FROM decisions {where} ORDER BY id DESC LIMIT ?", params
            ).fetchall()
        return [dict(r) for r in rows]

    def performance_pnls(self) -> list[float]:
        """Realized P/Ls of executed decisions that have a recorded result."""
        with get_connection(self._settings) as conn:
            rows = conn.execute(
                "SELECT pnl FROM decisions WHERE pnl IS NOT NULL"
            ).fetchall()
        return [float(r["pnl"]) for r in rows]

    def decision_counts(self) -> dict[str, int]:
        """Counts of EXECUTE vs NO_TRADE decisions (decision-quality summary)."""
        with get_connection(self._settings) as conn:
            rows = conn.execute(
                "SELECT decision, COUNT(*) AS n FROM decisions GROUP BY decision"
            ).fetchall()
        return {r["decision"]: int(r["n"]) for r in rows}

