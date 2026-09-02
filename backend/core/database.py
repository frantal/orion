"""SQLite persistence layer.

Provides schema initialization and a lightweight connection helper. The schema
is deliberately additive (``CREATE TABLE IF NOT EXISTS``) so it can be extended
across phases. Designed to be swappable for PostgreSQL later — all access goes
through :func:`get_connection`.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path

from backend.core.config import Settings, get_settings
from backend.core.logging import get_logger

logger = get_logger("database")

# --- Schema ---------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at         TEXT NOT NULL,
    symbol             TEXT NOT NULL,
    strategy           TEXT,
    market_regime      TEXT,
    thesis             TEXT,
    counter_thesis     TEXT,
    alpha_score        REAL,
    risk_score         REAL,
    liquidity_score    REAL,
    expected_value     REAL,
    risk_reward        REAL,
    decision           TEXT NOT NULL,
    reason             TEXT,
    risk_governor      TEXT,
    execution_status   TEXT,
    order_id           TEXT,
    result             TEXT,
    pnl                REAL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at   TEXT NOT NULL,
    agent        TEXT NOT NULL,
    action       TEXT NOT NULL,
    input        TEXT,
    output       TEXT,
    error        TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at        TEXT NOT NULL,
    client_order_id   TEXT NOT NULL UNIQUE,
    symbol            TEXT NOT NULL,
    strategy          TEXT,
    status            TEXT NOT NULL,
    payload           TEXT,
    broker_order_id   TEXT
);

CREATE INDEX IF NOT EXISTS idx_decisions_symbol ON decisions(symbol);
CREATE INDEX IF NOT EXISTS idx_decisions_created_at ON decisions(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_log(created_at);
"""


def _resolve_path(settings: Settings) -> Path:
    path = settings.sqlite_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def init_db(settings: Settings | None = None) -> Path:
    """Create the database file and schema if they do not exist.

    Returns the resolved database path.
    """
    settings = settings or get_settings()
    path = _resolve_path(settings)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
    logger.info("database initialized", extra={"path": str(path)})
    return path


@contextmanager
def get_connection(settings: Settings | None = None) -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection with row access by column name."""
    settings = settings or get_settings()
    path = _resolve_path(settings)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def check_db(settings: Settings | None = None) -> bool:
    """Return True if the database is reachable and the schema is present."""
    settings = settings or get_settings()
    try:
        with get_connection(settings) as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                ("decisions",),
            )
            return cur.fetchone() is not None
    except sqlite3.Error as exc:
        logger.error("database check failed", extra={"error": str(exc)})
        return False
