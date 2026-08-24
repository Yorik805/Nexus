"""Search operation implementation for the Nexus Memory Plugin.

This module queries the memories table in the SQLite database and returns
lightweight results without full content payload.
"""

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


def _validate_search_payload(data: dict) -> tuple[bool, str, dict[str, Any]]:
    if not isinstance(data, dict):
        return False, "SEARCH requires a dictionary payload.", {}

    # 'type' is required and selects SQLITE or VECTOR search
    search_type = data.get("type")
    if not isinstance(search_type, str) or not search_type.strip():
        return False, "type must be a non-empty string and be 'SQLITE' or 'VECTOR'.", {}
    search_type = search_type.strip().upper()
    if search_type not in {"SQLITE", "VECTOR"}:
        return False, "type must be 'SQLITE' or 'VECTOR'.", {}

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

    include_deleted = data.get("include_deleted")
    if include_deleted is not None and not isinstance(include_deleted, bool):
        return False, "include_deleted must be a boolean or null.", {}

    limit = data.get("limit")
    if limit is None:
        limit = 10
    elif isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        return False, "limit must be a positive integer or null.", {}

    return True, "", {
        "type": search_type,
        "query": query.strip(),
        "category": category,
        "tags": tags,
        "limit": limit,
        "include_deleted": bool(include_deleted),
    }


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _search_memories(
    query: str,
    category: str | None,
    tags: list[str] | None,
    include_deleted: bool,
    limit: int,
) -> list[dict[str, Any]]:
    ensure_database_ready()
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

    if not include_deleted:
        sql.append("AND (deleted = 0 OR deleted IS NULL)")

    sql.append("ORDER BY created_at DESC")
    sql.append("LIMIT ?")
    params.append(limit)

    query_sql = " ".join(sql)

    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
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
    # Delegate based on requested search type
    if normalized["type"] == "SQLITE":
        results = _search_memories(
            normalized["query"],
            normalized["category"],
            normalized["tags"],
            normalized["include_deleted"],
            normalized["limit"],
        )
        if not results:
            return _build_response("SUCCESS", "No matching memories found.", {"results": []})
        return _build_response("SUCCESS", f"Found {len(results)} matching memories.", {"results": results})

    # VECTOR search
    try:
        from ..vector_store import query_vector

        vector_results = query_vector(normalized["query"], limit=normalized["limit"], include_deleted=normalized["include_deleted"])  # type: ignore
        # Map vector results to lightweight result format
        mapped: list[dict[str, Any]] = []
        for entry in vector_results:
            mapped.append(
                {
                    "memory_id": entry.get("memory_id"),
                    "title": entry.get("title"),
                    "category": entry.get("category"),
                    "created_at": entry.get("created_at"),
                }
            )
        if not mapped:
            return _build_response("SUCCESS", "No matching memories found.", {"results": []})
        return _build_response("SUCCESS", f"Found {len(mapped)} matching memories.", {"results": mapped})
    except ImportError:
        return _build_response("ERROR", "Vector search requested but dependencies are not installed.")
    except Exception as exc:
        return _build_response("ERROR", f"Failed to perform vector search: {exc}")


# TODO:
# - Add SQLite FTS5 full-text search support for title/content.
# - Add embedding-based semantic search for natural language queries.
# - Add result ranking by relevance, freshness, or tags.
# - Add relationship-aware search across related memory items.
