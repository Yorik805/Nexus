"""List operation implementation for the Nexus Memory Plugin."""

from __future__ import annotations

import sqlite3
from typing import Any

from ..database import DATABASE_PATH, ensure_database_ready


def _build_response(status: str, message: str, data: dict | None = None) -> dict:
    return {
        "status": status,
        "message": message,
        "data": data or {},
    }


def _validate_list_payload(data: dict) -> tuple[bool, str, dict[str, Any]]:
    if not isinstance(data, dict):
        return False, "LIST requires a dictionary payload.", {}

    category = data.get("category")
    if category is not None:
        if not isinstance(category, str) or not category.strip():
            return False, "category must be a non-empty string or null.", {}
        category = category.strip().upper()

    limit = data.get("limit")
    if limit is None:
        limit = 20
    elif isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        return False, "limit must be a positive integer or null.", {}

    include_deleted = data.get("include_deleted", False)
    if not isinstance(include_deleted, bool):
        return False, "include_deleted must be a boolean.", {}

    return True, "", {
        "category": category,
        "limit": limit,
        "include_deleted": include_deleted,
    }


def list_memories(data: dict) -> dict:
    """List memories with optional filtering and ordering."""
    is_valid, error_message, normalized = _validate_list_payload(data)
    if not is_valid:
        return _build_response("ERROR", error_message)

    ensure_database_ready()

    sql = [
        "SELECT memory_id, title, category, created_at, version",
        "FROM memories",
        "WHERE 1 = 1",
    ]
    params: list[Any] = []

    if normalized["category"] is not None:
        sql.append("AND category = ?")
        params.append(normalized["category"])

    if not normalized["include_deleted"]:
        sql.append("AND (deleted = 0 OR deleted IS NULL)")

    sql.append("ORDER BY created_at DESC")
    sql.append("LIMIT ?")
    params.append(normalized["limit"])

    query_sql = " ".join(sql)

    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()
            cursor.execute(query_sql, params)
            results = [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error:
        return _build_response("ERROR", "Failed to list memories from the database.")

    return _build_response("SUCCESS", "Memories retrieved successfully.", {"results": results})
