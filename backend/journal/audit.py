"""Audit logger — every agent action is recorded (section 21)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from backend.core.config import Settings, get_settings
from backend.core.database import get_connection
from backend.core.logging import get_logger

logger = get_logger("journal.audit")


class AuditLogger:
    """Append-only audit trail persisted to SQLite."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def log(
        self,
        agent: str,
        action: str,
        input_data: Any = None,
        output_data: Any = None,
        error: str | None = None,
    ) -> None:
        try:
            with get_connection(self._settings) as conn:
                conn.execute(
                    "INSERT INTO audit_log (created_at, agent, action, input, output, error) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        datetime.now(timezone.utc).isoformat(),
                        agent,
                        action,
                        _dump(input_data),
                        _dump(output_data),
                        error,
                    ),
                )
        except Exception as exc:  # noqa: BLE001 - auditing must never break the pipeline
            logger.error("audit write failed", extra={"error": str(exc)})

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        with get_connection(self._settings) as conn:
            rows = conn.execute(
                "SELECT created_at, agent, action, input, output, error "
                "FROM audit_log ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]


def _dump(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, default=str)
    except (TypeError, ValueError):
        return str(value)
