"""Search files operation for the Nexus File System Plugin.

Searches for files matching patterns.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

from ..filesystem_helpers import (
    build_response,
    get_file_metadata,
    is_dir,
    is_file,
    validate_path,
)


def search(data: dict) -> dict:
    """Search for files matching a pattern in a directory.

    Request format:
    {
        "path": str,
        "pattern": str (optional, default "*"),
        "recursive": bool (optional, default false),
        "type": str (optional, "file" | "directory" | "any", default "any")
    }

    Returns:
        Standard response with lightweight metadata of matching entries
    """
    if not isinstance(data, dict):
        return build_response("ERROR", "SEARCH requires a dictionary payload.")

    # Validate path
    is_valid, error_msg, path = validate_path(data.get("path"))
    if not is_valid:
        return build_response("ERROR", error_msg)

    # Check if directory
    if not is_dir(path):
        return build_response("ERROR", "Path is not a directory or does not exist.")

    # Get search parameters
    pattern = str(data.get("pattern", "*")).strip() or "*"
    recursive = bool(data.get("recursive", False))
    search_type = str(data.get("type", "any")).strip().lower()

    if search_type not in ("file", "directory", "any"):
        return build_response("ERROR", "type must be 'file', 'directory', or 'any'.")

    # Search
    results = []
    try:
        if recursive:
            entries = path.rglob("*")
        else:
            entries = path.glob("*")

        for entry in sorted(entries):
            # Match pattern (only against the name, not the full path)
            if not fnmatch.fnmatch(entry.name, pattern):
                continue

            # Filter by type
            if search_type == "file" and not is_file(entry):
                continue
            elif search_type == "directory" and not is_dir(entry):
                continue

            # Get metadata
            metadata = get_file_metadata(entry)
            if metadata:
                results.append(metadata)

    except (OSError, ValueError):
        return build_response("ERROR", "Failed to search directory.")

    return build_response(
        "SUCCESS",
        f"Found {len(results)} matching entries.",
        {
            "path": str(path),
            "pattern": pattern,
            "results": results,
            "count": len(results),
        },
    )
