"""Get operation implementation for the Nexus Memory Plugin.

This module returns the full memory record for a given memory_id.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .database import DATABASE_PATH, ensure_database_ready


def _build_response(status: str, message: str, data: dict | None = None) -> dict:
    return {
        "status": status,
        "message": message,
        "data": data or {},
    }


def _normalize_row(row: sqlite3.Row) -> dict[str, Any]:
    record = dict(row)
    try:
        record["tags"] = json.loads(record.get("tags", "[]"))
    except (json.JSONDecodeError, TypeError):
        record["tags"] = []

    deleted_value = record.get("deleted")
    record["deleted"] = bool(deleted_value) if deleted_value is not None else False
    return record


def get(data: dict) -> dict:
    """Fetch a complete memory record by memory_id."""
    if not isinstance(data, dict):
        return _build_response("ERROR", "GET requires a dictionary payload.")

    memory_id = data.get("memory_id")
    if not isinstance(memory_id, str) or not memory_id.strip():
        return _build_response("ERROR", "memory_id must be a non-empty string.")
    memory_id = memory_id.strip()

    include_deleted = data.get("include_deleted", False)
    if not isinstance(include_deleted, bool):
        return _build_response("ERROR", "include_deleted must be a boolean.")

    ensure_database_ready()

    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM memories WHERE memory_id = ?", (memory_id,))
            row = cursor.fetchone()
    except sqlite3.Error:
        return _build_response("ERROR", "Failed to fetch memory from the database.")

    if row is None:
        return _build_response("ERROR", "Memory not found.")

    record = _normalize_row(row)
    if record.get("deleted") and not include_deleted:
        return _build_response("ERROR", "Memory has been deleted.")

    return _build_response("SUCCESS", "Memory fetched successfully.", {"memory": record})
