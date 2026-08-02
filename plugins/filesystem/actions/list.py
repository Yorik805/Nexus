"""List directory operation for the Nexus File System Plugin.

Lists contents of a directory with metadata.
"""

from __future__ import annotations

from pathlib import Path

from ..filesystem_helpers import (
    build_response,
    get_directory_contents,
    is_dir,
    validate_path,
)


def list(data: dict) -> dict:
    """List contents of a directory.

    Request format:
    {
        "path": str,
        "include_hidden": bool (optional, default false)
    }

    Returns:
        Standard response with directory entries
    """
    if not isinstance(data, dict):
        return build_response("ERROR", "LIST requires a dictionary payload.")

    # Validate path
    is_valid, error_msg, path = validate_path(data.get("path"))
    if not is_valid:
        return build_response("ERROR", error_msg)

    # Check if directory
    if not is_dir(path):
        return build_response("ERROR", "Path is not a directory or does not exist.")

    # Get include_hidden flag
    include_hidden = bool(data.get("include_hidden", False))

    # List directory
    entries = get_directory_contents(path, include_hidden=include_hidden)
    if entries is None:
        return build_response("ERROR", "Failed to list directory.")

    return build_response(
        "SUCCESS",
        f"Listed {len(entries)} entries.",
        {
            "path": str(path),
            "entries": entries,
            "count": len(entries),
        },
    )
