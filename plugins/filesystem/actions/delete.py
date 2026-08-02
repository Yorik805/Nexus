"""Delete file operation for the Nexus File System Plugin.

Deletes files or directories from the file system.
"""

from __future__ import annotations

from pathlib import Path

from ..filesystem_helpers import (
    build_response,
    path_exists,
    safe_delete,
    validate_path,
)


def delete(data: dict) -> dict:
    """Delete a file or directory.

    Request format:
    {
        "path": str,
        "recursive": bool (optional, default false)
    }

    Returns:
        Standard response with deletion confirmation
    """
    if not isinstance(data, dict):
        return build_response("ERROR", "DELETE requires a dictionary payload.")

    # Validate path
    is_valid, error_msg, path = validate_path(data.get("path"))
    if not is_valid:
        return build_response("ERROR", error_msg)

    # Get recursive flag
    recursive = bool(data.get("recursive", False))

    # Delete
    success, error_msg = safe_delete(path, recursive=recursive)
    if not success:
        return build_response("ERROR", error_msg)

    return build_response(
        "SUCCESS",
        "Path deleted successfully.",
        {"path": str(path)},
    )
