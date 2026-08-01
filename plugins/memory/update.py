"""Update operation implementation for the Nexus Memory Plugin.

This module updates an existing memory record in SQLite using only the fields
provided in the request payload.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .database import DATABASE_PATH, ensure_database_ready

VALID_CATEGORIES = {"PROJECT", "PERSON", "IDEA", "PREFERENCE"}


def _build_response(status: str, message: str, data: dict | None = None) -> dict:
    return {
        "status": status,
        "message": message,
        "data": data or {},
    }


def _get_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_string_field(payload: dict, field_name: str) -> tuple[bool, str, str | None]:
    value = payload.get(field_name)
    if value is None:
        return True, "", None
    if not isinstance(value, str) or not value.strip():
        return False, f"{field_name} must be a non-empty string.", None
    return True, "", value.strip()


def _validate_tags(tags: Any) -> tuple[bool, str, list[str] | None]:
    if tags is None:
        return True, "", None
    if not isinstance(tags, list):
        return False, "tags must be a list of strings.", None
    normalized_tags: list[str] = []
    for tag in tags:
        if not isinstance(tag, str) or not tag.strip():
            return False, "tags must contain only non-empty strings.", None
        normalized_tags.append(tag.strip())
    return True, "", normalized_tags


def _fetch_memory(memory_id: str) -> dict[str, Any] | None:
    ensure_database_ready()
    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()
            cursor.execute(
                "SELECT memory_id, version FROM memories WHERE memory_id = ?",
                (memory_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error:
        return None


def _update_memory(memory_id: str, values: dict[str, Any], version: int, updated_at: str) -> bool:
    columns = []
    params: list[Any] = []

    for key, value in values.items():
        columns.append(f"{key} = ?")
        params.append(value)

    columns.append("updated_at = ?")
    params.append(updated_at)
    columns.append("version = ?")
    params.append(version)
    params.append(memory_id)

    sql = f"UPDATE memories SET {', '.join(columns)} WHERE memory_id = ?"

    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            cursor = connection.cursor()
            cursor.execute(sql, params)
            connection.commit()
            return cursor.rowcount == 1
    except sqlite3.Error:
        return False


def update(data: dict) -> dict:
    """Update an existing memory record with the provided changes."""
    if not isinstance(data, dict):
        return _build_response(
            "ERROR",
            "UPDATE requires a dictionary payload.",
        )

    memory_id = data.get("memory_id")
    if not isinstance(memory_id, str) or not memory_id.strip():
        return _build_response(
            "ERROR",
            "memory_id must be a non-empty string.",
        )
    memory_id = memory_id.strip()

    changes = data.get("changes")
    if not isinstance(changes, dict) or not changes:
        return _build_response(
            "ERROR",
            "changes must be a non-empty dictionary.",
        )

    # Validate each change field individually.
    update_values: dict[str, Any] = {}

    if "title" in changes:
        valid, message, title = _validate_string_field(changes, "title")
        if not valid:
            return _build_response("ERROR", message)
        update_values["title"] = title

    if "content" in changes:
        valid, message, content = _validate_string_field(changes, "content")
        if not valid:
            return _build_response("ERROR", message)
        update_values["content"] = content

    if "category" in changes:
        valid, message, category = _validate_string_field(changes, "category")
        if not valid:
            return _build_response("ERROR", message)
        category = category.strip().upper()
        if category not in VALID_CATEGORIES:
            return _build_response(
                "ERROR",
                f"category must be one of: {', '.join(sorted(VALID_CATEGORIES))}.",
            )
        update_values["category"] = category

    if "tags" in changes:
        valid, message, tags = _validate_tags(changes.get("tags"))
        if not valid:
            return _build_response("ERROR", message)
        update_values["tags"] = json.dumps(tags, separators=(",", ":"))

    allowed_keys = {"title", "content", "category", "tags"}
    unsupported_keys = set(changes) - allowed_keys
    if unsupported_keys:
        return _build_response(
            "ERROR",
            f"Unsupported change fields: {', '.join(sorted(unsupported_keys))}.",
        )

    if not update_values:
        return _build_response(
            "ERROR",
            "No valid change fields were provided.",
        )

    existing = _fetch_memory(memory_id)
    if existing is None:
        return _build_response(
            "ERROR",
            "Memory not found.",
        )

    updated_at = _get_timestamp()
    try:
        current_version = int(existing.get("version", 0))
    except (TypeError, ValueError):
        current_version = 0

    next_version = current_version + 1

    if not _update_memory(memory_id, update_values, next_version, updated_at):
        return _build_response(
            "ERROR",
            "Failed to update memory.",
        )

    return _build_response(
        "SUCCESS",
        "Memory updated successfully.",
        {
            "memory_id": memory_id,
            "version": next_version,
            "updated_at": updated_at,
        },
    )
