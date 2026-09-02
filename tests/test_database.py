"""Tests for the database layer."""

from __future__ import annotations

from backend.core.database import check_db, get_connection, init_db


def test_init_db_creates_file_and_schema(tmp_settings) -> None:
    path = init_db(tmp_settings)
    assert path.exists()
    assert check_db(tmp_settings) is True


def test_tables_exist(tmp_settings) -> None:
    init_db(tmp_settings)
    with get_connection(tmp_settings) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        names = {r["name"] for r in rows}
    assert {"decisions", "audit_log", "orders"} <= names


def test_orders_client_order_id_unique(tmp_settings) -> None:
    init_db(tmp_settings)
    with get_connection(tmp_settings) as conn:
        conn.execute(
            "INSERT INTO orders (created_at, client_order_id, symbol, status) "
            "VALUES (?, ?, ?, ?)",
            ("2026-01-01T00:00:00Z", "coid-1", "SPY", "new"),
        )
    duplicated = False
    try:
        with get_connection(tmp_settings) as conn:
            conn.execute(
                "INSERT INTO orders (created_at, client_order_id, symbol, status) "
                "VALUES (?, ?, ?, ?)",
                ("2026-01-01T00:00:01Z", "coid-1", "SPY", "new"),
            )
    except Exception:
        duplicated = True
    assert duplicated is True
