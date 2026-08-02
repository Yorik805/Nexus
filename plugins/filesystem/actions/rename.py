"""Rename file operation for the Nexus File System Plugin.

Renames a file or directory in place.
"""

from __future__ import annotations

from pathlib import Path

from ..filesystem_helpers import (
    build_response,
    safe_rename,
    validate_path,
)


def rename(data: dict) -> dict:
    """Rename a file or directory.

    Request format:
    {
        "path": str,
        "new_name": str
    }

    Returns:
        Standard response with old and new paths
    """
    if not isinstance(data, dict):
        return build_response("ERROR", "RENAME requires a dictionary payload.")

    # Validate path
    is_valid, error_msg, path = validate_path(data.get("path"))
    if not is_valid:
        return build_response("ERROR", error_msg)

    # Get new name
    new_name = data.get("new_name")
    if not isinstance(new_name, str) or not new_name.strip():
        return build_response("ERROR", "new_name must be a non-empty string.")
    new_name = new_name.strip()

    # Rename
    success, error_msg = safe_rename(path, new_name)
    if not success:
        return build_response("ERROR", error_msg)

    new_path = path.parent / new_name
    return build_response(
        "SUCCESS",
        "Path renamed successfully.",
        {"old_path": str(path), "new_path": str(new_path)},
    )
