"""Delete operation implementation for the Nexus Memory Plugin.

This module performs a soft delete by marking a memory as deleted and
recording the deletion timestamp.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from ..database import DATABASE_PATH, ensure_database_ready


def _build_response(status: str, message: str, data: dict | None = None) -> dict:
    return {
        "status": status,
        "message": message,
        "data": data or {},
    }


def _get_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def delete(data: dict) -> dict:
    """Soft delete a memory by memory_id."""
    if not isinstance(data, dict):
        return _build_response("ERROR", "DELETE requires a dictionary payload.")

    memory_id = data.get("memory_id")
    if not isinstance(memory_id, str) or not memory_id.strip():
        return _build_response("ERROR", "memory_id must be a non-empty string.")
    memory_id = memory_id.strip()

    ensure_database_ready()
    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT memory_id FROM memories WHERE memory_id = ?", (memory_id,))
            if cursor.fetchone() is None:
                return _build_response("ERROR", "Memory not found.")

            cursor.execute(
                "UPDATE memories SET deleted = 1, deleted_at = ? WHERE memory_id = ?",
                (_get_timestamp(), memory_id),
            )
            connection.commit()
    except sqlite3.Error:
        return _build_response("ERROR", "Failed to delete memory in the database.")

    return _build_response("SUCCESS", "Memory deleted successfully.", {"memory_id": memory_id})
