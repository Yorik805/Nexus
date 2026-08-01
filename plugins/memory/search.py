"""Search operation implementation for the Nexus Memory Plugin.

This module queries the memories table in the SQLite database and returns
lightweight results without full content payload.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


_DATABASE_PATH = Path(__file__).resolve().parent / "database" / "memory.db"


def _build_response(status: str, message: str, data: dict | None = None) -> dict:
    return {
        "status": status,
        "message": message,
        "data": data or {},
    }


def _validate_search_payload(data: dict) -> tuple[bool, str, dict[str, Any]]:
    if not isinstance(data, dict):
        return False, "SEARCH requires a dictionary payload.", {}

    query = data.get("query")
    if not isinstance(query, str) or not query.strip():
        return False, "query must be a non-empty string.", {}

    category = data.get("category")
    if category is not None:
        if not isinstance(category, str) or not category.strip():
            return False, "category must be a non-empty string or null.", {}
        category = category.strip().upper()

    tags = data.get("tags")
    if tags is not None:
        if not isinstance(tags, list):
            return False, "tags must be a list of strings or null.", {}
        normalized_tags: list[str] = []
        for tag in tags:
            if not isinstance(tag, str) or not tag.strip():
                return False, "tags must contain only non-empty strings.", {}
            normalized_tags.append(tag.strip())
        tags = normalized_tags

    limit = data.get("limit")
    if limit is None:
        limit = 10
    elif isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        return False, "limit must be a positive integer or null.", {}

    return True, "", {
        "query": query.strip(),
        "category": category,
        "tags": tags,
        "limit": limit,
    }


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _ensure_database_directory() -> None:
    _DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _search_memories(query: str, category: str | None, tags: list[str] | None, limit: int) -> list[dict[str, Any]]:
    _ensure_database_directory()
    like_pattern = f"%{_escape_like(query)}%"

    sql = [
        "SELECT memory_id, title, category, created_at",
        "FROM memories",
        "WHERE (title LIKE ? ESCAPE '\\' OR content LIKE ? ESCAPE '\\')",
    ]
    params: list[Any] = [like_pattern, like_pattern]

    if category is not None:
        sql.append("AND category = ?")
        params.append(category)

    if tags is not None:
        for tag in tags:
            escaped_tag = _escape_like(tag)
            sql.append("AND tags LIKE ? ESCAPE '\\'")
            params.append(f"%\"{escaped_tag}\"%")

    sql.append("ORDER BY created_at DESC")
    sql.append("LIMIT ?")
    params.append(limit)

    query_sql = " ".join(sql)

    try:
        with sqlite3.connect(_DATABASE_PATH) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()
            cursor.execute(query_sql, params)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        return []
    except sqlite3.Error:
        return []


def search(data: dict) -> dict:
    """Search stored memories and return lightweight metadata results."""
    is_valid, error_message, normalized = _validate_search_payload(data)
    if not is_valid:
        return _build_response("ERROR", error_message)

    results = _search_memories(
        normalized["query"],
        normalized["category"],
        normalized["tags"],
        normalized["limit"],
    )

    if not results:
        return _build_response(
            "SUCCESS",
            "No matching memories found.",
            {"results": []},
        )

    return _build_response(
        "SUCCESS",
        f"Found {len(results)} matching memories.",
        {"results": results},
    )


# TODO:
# - Add SQLite FTS5 full-text search support for title/content.
# - Add embedding-based semantic search for natural language queries.
# - Add result ranking by relevance, freshness, or tags.
# - Add relationship-aware search across related memory items.
