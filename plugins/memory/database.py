"""Shared database helpers for the Nexus Memory Plugin.

This module centralizes database path resolution, initialization, and schema
migration logic across all memory operations.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parent / "database" / "memory.db"

_BASE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS memories (
    memory_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL
);
"""


def _ensure_database_directory() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _table_has_column(column_name: str) -> bool:
    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            cursor = connection.execute("PRAGMA table_info(memories)")
            return any(row[1] == column_name for row in cursor.fetchall())
    except sqlite3.Error:
        return False


def ensure_database_ready() -> None:
    """Create the base memories table and perform any required schema migration."""
    _ensure_database_directory()
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.executescript(_BASE_TABLE_SQL)
        connection.commit()
    _ensure_deleted_columns()


def _ensure_deleted_columns() -> None:
    """Add soft-delete columns to the memories table if they are missing."""
    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            cursor = connection.cursor()
            if not _table_has_column("deleted"):
                cursor.execute("ALTER TABLE memories ADD COLUMN deleted INTEGER DEFAULT 0")
            if not _table_has_column("deleted_at"):
                cursor.execute("ALTER TABLE memories ADD COLUMN deleted_at TEXT")
            connection.commit()
    except sqlite3.Error:
        # Migration is best-effort; existing data should remain intact.
        pass
