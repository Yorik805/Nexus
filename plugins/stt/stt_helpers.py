from __future__ import annotations

from typing import Any


def build_response(status: str, message: str, data: dict | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "message": message,
        "data": data or {},
    }
