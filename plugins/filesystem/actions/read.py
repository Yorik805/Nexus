"""Read file operation for the Nexus File System Plugin.

Retrieves the complete contents of a file.
"""

from __future__ import annotations

from pathlib import Path

from ..filesystem_helpers import (
    build_response,
    is_file,
    normalize_encoding,
    safe_read_file,
    validate_path,
)


def read(data: dict) -> dict:
    """Read the contents of a file.

    Request format:
    {
        "path": str,
        "encoding": str (optional, default "utf-8")
    }

    Returns:
        Standard response with file contents in data["content"]
    """
    if not isinstance(data, dict):
        return build_response("ERROR", "READ requires a dictionary payload.")

    # Validate path
    is_valid, error_msg, path = validate_path(data.get("path"))
    if not is_valid:
        return build_response("ERROR", error_msg)

    # Check if file exists
    if not is_file(path):
        return build_response("ERROR", "Path is not a file or does not exist.")

    # Get encoding
    encoding = normalize_encoding(data.get("encoding"))

    # Read file
    success, content_or_error = safe_read_file(path, encoding)
    if not success:
        return build_response("ERROR", content_or_error)

    # Return content (as string if possible, base64 encoded if binary)
    if isinstance(content_or_error, str):
        return build_response(
            "SUCCESS",
            "File read successfully.",
            {"content": content_or_error, "encoding": encoding},
        )
    else:
        # Binary file - encode as base64
        import base64
        encoded = base64.b64encode(content_or_error).decode("ascii")
        return build_response(
            "SUCCESS",
            "File read successfully (binary).",
            {"content": encoded, "encoding": "base64"},
        )
