"""Disconnect a device."""

from __future__ import annotations

from runtime import get_device_store


def disconnect_device(data: dict) -> dict:
    device_id = str(data.get("device_id", "")).strip()
    if not device_id:
        return {"status": "ERROR", "message": "device_id is required.", "data": {}}
    
    store = get_device_store()
    device = store.get_device(device_id)
    if device is None:
        return {"status": "ERROR", "message": f"Device not found: {device_id}", "data": {}}
    
    store.unregister_device(device_id)
    return {
        "status": "SUCCESS",
        "message": f"Device {device_id} disconnected.",
        "data": {},
    }
