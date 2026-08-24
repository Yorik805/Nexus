from __future__ import annotations

from ..model_loader import get_current_device
from ..stt_helpers import build_response


def get_device_action(data: dict) -> dict:
    if not isinstance(data, dict):
        return build_response("ERROR", "GET_DEVICE requires a dictionary payload.")

    device = get_current_device()
    if device is None:
        return build_response("ERROR", "No device is selected because no model is loaded.")

    return build_response(
        "SUCCESS",
        "Current device retrieved successfully.",
        {"device": device},
    )
