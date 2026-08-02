"""Copy file operation for the Nexus File System Plugin.

Copies files or directories to a new location.
"""

from __future__ import annotations

from pathlib import Path

from ..filesystem_helpers import (
    build_response,
    safe_copy,
    validate_path,
)


def copy(data: dict) -> dict:
    """Copy a file or directory to a new location.

    Request format:
    {
        "source": str,
        "destination": str,
        "recursive": bool (optional, default true)
    }

    Returns:
        Standard response with source and destination paths
    """
    if not isinstance(data, dict):
        return build_response("ERROR", "COPY requires a dictionary payload.")

    # Validate source path
    is_valid, error_msg, source_path = validate_path(data.get("source"))
    if not is_valid:
        return build_response("ERROR", f"Invalid source path: {error_msg}")

    # Validate destination path
    is_valid, error_msg, dest_path = validate_path(data.get("destination"))
    if not is_valid:
        return build_response("ERROR", f"Invalid destination path: {error_msg}")

    # Get recursive flag
    recursive = bool(data.get("recursive", True))

    # Copy
    success, error_msg = safe_copy(source_path, dest_path, recursive=recursive)
    if not success:
        return build_response("ERROR", error_msg)

    return build_response(
        "SUCCESS",
        "Path copied successfully.",
        {"source": str(source_path), "destination": str(dest_path)},
    )
