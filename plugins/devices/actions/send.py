"""Send a message to a device."""

from __future__ import annotations

from typing import Any

from runtime import get_device_store


def send_message(data: dict) -> dict:
    device_id = str(data.get("device_id", "")).strip()
    message = str(data.get("message", "")).strip()
    
    if not device_id:
        return {"status": "ERROR", "message": "device_id is required.", "data": {}}
    if not message:
        return {"status": "ERROR", "message": "message is required.", "data": {}}
    
    store = get_device_store()
    device = store.get_device(device_id)
    if device is None:
        return {"status": "ERROR", "message": f"Device not found: {device_id}", "data": {}}
    
    message_id = store.add_pending_message(device_id, message)
    return {
        "status": "SUCCESS",
        "message": f"Message queued for device {device_id}.",
        "data": {"message_id": message_id, "device_id": device_id, "message": message},
    }
