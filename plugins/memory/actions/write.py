"""Write operation implementation for the Nexus Memory Plugin.

This module handles validation, memory normalization, and persistence to a
SQLite database located in plugins/memory/database/memory.db.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from typing import Any

from ..database import DATABASE_PATH, ensure_database_ready


# Predefined categories to ensure consistent taxonomy and avoid typos.
VALID_CATEGORIES = {"PROJECT", "PERSON", "IDEA", "PREFERENCE"}


def _get_timestamp() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _validate_string_field(payload: dict, field_name: str) -> tuple[bool, str]:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        return False, f"{field_name} must be a non-empty string."
    return True, value.strip()


def _validate_tags(payload: dict) -> tuple[bool, list[str] | str]:
    tags = payload.get("tags")
    if not isinstance(tags, list):
        return False, "tags must be a list of strings."

    normalized_tags: list[str] = []
    for tag in tags:
        if not isinstance(tag, str) or not tag.strip():
            return False, "tags must contain only non-empty strings."
        normalized_tags.append(tag.strip())

    return True, normalized_tags


def _insert_memory(record: dict[str, Any]) -> None:
    """Insert a validated memory record into the SQLite database."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO memories (
                memory_id,
                title,
                category,
                content,
                tags,
                created_at,
                updated_at,
                version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record["memory_id"],
                record["title"],
                record["category"],
                record["content"],
                record["tags"],
                record["created_at"],
                record["updated_at"],
                record["version"],
            ],
        )
        connection.commit()


def _build_response(status: str, message: str, data: dict | None = None) -> dict:
    return {
        "status": status,
        "message": message,
        "data": data or {},
    }


def write(data: dict) -> dict:
    """Validate and persist a memory item.

    Expected payload:
    {
        "title": str,
        "category": str,
        "content": str,
        "tags": list[str]
    }

    Returns a standard response dictionary.
    """
    if not isinstance(data, dict):
        return _build_response(
            "ERROR",
            "WRITE requires a dictionary payload.",
        )

    # Validate required string fields.
    is_valid, title_or_error = _validate_string_field(data, "title")
    if not is_valid:
        return _build_response("ERROR", title_or_error)

    is_valid, category_or_error = _validate_string_field(data, "category")
    if not is_valid:
        return _build_response("ERROR", category_or_error)

    is_valid, content_or_error = _validate_string_field(data, "content")
    if not is_valid:
        return _build_response("ERROR", content_or_error)

    # Normalize and validate category constant.
    category = category_or_error.strip().upper()
    if category not in VALID_CATEGORIES:
        return _build_response(
            "ERROR",
            f"category must be one of: {', '.join(sorted(VALID_CATEGORIES))}.",
        )

    is_valid, tags_or_error = _validate_tags(data)
    if not is_valid:
        return _build_response("ERROR", tags_or_error)

    tags = tags_or_error

    # Prepare the memory record.
    memory_id = str(uuid.uuid4())
    timestamp = _get_timestamp()
    record = {
        "memory_id": memory_id,
        "title": title_or_error,
        "category": category,
        "content": content_or_error,
        "tags": json.dumps(tags, separators=(",", ":")),
        "created_at": timestamp,
        "updated_at": timestamp,
        "version": 1,
    }

    try:
        ensure_database_ready()
        _insert_memory(record)
    except sqlite3.Error:
        return _build_response(
            "ERROR",
            "Failed to store memory in the database.",
        )
    except Exception:
        return _build_response(
            "ERROR",
            "Unexpected error while storing memory.",
        )

    return _build_response(
        "SUCCESS",
        "Memory stored successfully.",
        {
            "memory_id": memory_id,
            "created_at": timestamp,
            "version": 1,
        },
    )
