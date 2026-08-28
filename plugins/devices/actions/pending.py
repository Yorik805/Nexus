"""List pending messages from devices."""

from __future__ import annotations

from runtime import get_device_store


def list_pending(data: dict) -> dict:
    device_id = str(data.get("device_id", "")).strip() or None
    store = get_device_store()
    
    if device_id:
        pending = store.get_pending_messages(device_id)
        return {
            "status": "SUCCESS",
            "message": f"Found {len(pending)} pending message(s) for {device_id}.",
            "data": {"pending": pending, "device_id": device_id},
        }
    
    all_pending = store.get_all_pending_messages()
    total = sum(len(msgs) for msgs in all_pending.values())
    return {
        "status": "SUCCESS",
        "message": f"Found {total} pending message(s) across {len(all_pending)} device(s).",
        "data": {"pending": all_pending},
    }
