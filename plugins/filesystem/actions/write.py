"""Write file operation for the Nexus File System Plugin.

Creates or overwrites a file with the provided content.
"""

from __future__ import annotations

from pathlib import Path

from ..filesystem_helpers import (
    build_response,
    normalize_encoding,
    safe_write_file,
    validate_path,
)


def write(data: dict) -> dict:
    """Write content to a file (creates or overwrites).

    Request format:
    {
        "path": str,
        "content": str | bytes,
        "encoding": str (optional, default "utf-8")
    }

    Returns:
        Standard response with path information
    """
    if not isinstance(data, dict):
        return build_response("ERROR", "WRITE requires a dictionary payload.")

    # Validate path
    is_valid, error_msg, path = validate_path(data.get("path"))
    if not is_valid:
        return build_response("ERROR", error_msg)

    # Get content
    content = data.get("content")
    if content is None:
        return build_response("ERROR", "content is required.")
    if not isinstance(content, (str, bytes)):
        return build_response("ERROR", "content must be a string or bytes.")

    # Get encoding
    encoding = normalize_encoding(data.get("encoding"))

    # Write file
    success, error_msg = safe_write_file(path, content, encoding)
    if not success:
        return build_response("ERROR", error_msg)

    return build_response(
        "SUCCESS",
        "File written successfully.",
        {
            "path": str(path),
            "size": len(content),
            "encoding": encoding if isinstance(content, str) else "bytes",
        },
    )
