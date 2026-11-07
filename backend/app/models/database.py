"""
Calculation history stored in SQLite (standard-library ``sqlite3`` - no extra packages).

The database file lives next to ``main.py`` regardless of the directory you start
uvicorn from (the old relative path ``./calculator.db`` created a different, empty
database whenever the server was started from another folder).
Override the location with the CALCULATOR_DB environment variable.
"""

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

DB_PATH = Path(os.environ.get("CALCULATOR_DB") or Path(__file__).resolve().parents[2] / "calculator.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS calculation_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    expression      TEXT NOT NULL,
    result          TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    calculator_type TEXT NOT NULL
)
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(_connect()) as conn, conn:
        conn.execute(_SCHEMA)


def add_history(expression: str, result: str, calculator_type: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO calculation_history (expression, result, timestamp, calculator_type) VALUES (?, ?, ?, ?)",
            (expression, result, stamp, calculator_type),
        )


def _as_utc_iso(stamp: str) -> str:
    """Rows written by the old version have no timezone; treat them as UTC."""
    try:
        parsed = datetime.fromisoformat(stamp)
    except ValueError:
        return stamp
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat()


def get_history(limit: int = 50) -> List[Dict[str, object]]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT id, expression, result, timestamp, calculator_type "
            "FROM calculation_history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{**dict(row), "timestamp": _as_utc_iso(row["timestamp"])} for row in rows]


def clear_history() -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM calculation_history")
