"""Send a message to a device through the runtime communication manager."""

from __future__ import annotations

from runtime import get_device_communication_manager, get_device_store


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

    manager = get_device_communication_manager()
    event = {
        "type": "MESSAGE",
        "source": "NEXUS",
        "data": {"message": message},
    }
    delivered = manager.send(device_id, event)
    message_id = store.add_pending_message(device_id, message) if not delivered else None
    return {
        "status": "SUCCESS",
        "message": f"Message {'delivered immediately' if delivered else 'queued for device'} {device_id}.",
        "data": {
            "message_id": message_id or "live-delivery",
            "device_id": device_id,
            "message": message,
            "delivered_immediately": delivered,
        },
    }
