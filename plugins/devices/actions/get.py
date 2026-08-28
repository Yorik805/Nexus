"""Get device details."""

from __future__ import annotations

from runtime import get_device_store


def get_device(data: dict) -> dict:
    device_id = str(data.get("device_id", "")).strip()
    if not device_id:
        return {"status": "ERROR", "message": "device_id is required.", "data": {}}
    
    device = get_device_store().get_device(device_id)
    if device is None:
        return {"status": "ERROR", "message": f"Device not found: {device_id}", "data": {}}
    
    return {
        "status": "SUCCESS",
        "message": "Device found.",
        "data": {"device": device},
    }
