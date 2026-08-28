"""List all connected devices."""

from __future__ import annotations

from runtime import get_device_store


def list_devices(data: dict) -> dict:
    devices = get_device_store().list_devices()
    return {
        "status": "SUCCESS",
        "message": f"Found {len(devices)} device(s).",
        "data": {"devices": devices},
    }
