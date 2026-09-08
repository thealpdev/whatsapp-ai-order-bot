"""SQLite persistence: conversation history + orders."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    phone      TEXT NOT NULL,
    role       TEXT NOT NULL,          -- user | assistant | tool_call | tool_result
    content    TEXT NOT NULL,
    tool_name  TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_phone ON messages (phone, id);

CREATE TABLE IF NOT EXISTS orders (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    phone      TEXT NOT NULL,
    address    TEXT NOT NULL,
    items_json TEXT NOT NULL,
    total      REAL NOT NULL,
    status     TEXT NOT NULL DEFAULT 'received',
    created_at TEXT NOT NULL
);
"""


@dataclass
class StoredMessage:
    role: str
    content: str
    tool_name: str | None = None


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # --- conversation history -------------------------------------------------

    def add_message(
        self, phone: str, role: str, content: str, tool_name: str | None = None
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO messages (phone, role, content, tool_name, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (phone, role, content, tool_name, _now()),
            )

    def get_history(self, phone: str, limit: int = 20) -> list[StoredMessage]:
        """Most recent `limit` messages for a phone number, oldest first."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content, tool_name FROM messages"
                " WHERE phone = ? ORDER BY id DESC LIMIT ?",
                (phone, limit),
            ).fetchall()
        return [StoredMessage(r["role"], r["content"], r["tool_name"]) for r in reversed(rows)]

    # --- orders ---------------------------------------------------------------

    def create_order(self, phone: str, address: str, items: list[dict], total: float) -> dict:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO orders (phone, address, items_json, total, status, created_at)"
                " VALUES (?, ?, ?, ?, 'received', ?)",
                (phone, address, json.dumps(items, ensure_ascii=False), total, _now()),
            )
            order_id = cur.lastrowid
        return {
            "id": order_id,
            "phone": phone,
            "address": address,
            "items": items,
            "total": total,
            "status": "received",
        }

    def list_orders(self, limit: int = 100) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {
                "id": r["id"],
                "phone": r["phone"],
                "address": r["address"],
                "items": json.loads(r["items_json"]),
                "total": r["total"],
                "status": r["status"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
