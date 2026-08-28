"""Register a new device."""

from __future__ import annotations

from typing import Any

from runtime import get_device_store


def register_device(data: dict) -> dict:
    device_id = str(data.get("device_id", "")).strip()
    device_type = str(data.get("device_type", "")).strip()
    
    if not device_id:
        return {"status": "ERROR", "message": "device_id is required.", "data": {}}
    if not device_type:
        return {"status": "ERROR", "message": "device_type is required.", "data": {}}
    
    store = get_device_store()
    device = store.register_device(device_id, device_type)
    return {
        "status": "SUCCESS",
        "message": f"Device {device_id} registered.",
        "data": {"device": device},
    }
