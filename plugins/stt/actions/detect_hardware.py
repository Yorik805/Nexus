from __future__ import annotations

from ..hardware import detect_hardware as detect_hardware_impl
from ..stt_helpers import build_response


def detect_hardware(data: dict) -> dict:
    if not isinstance(data, dict):
        return build_response("ERROR", "DETECT_HARDWARE requires a dictionary payload.")

    detected = detect_hardware_impl()
    return build_response(
        "SUCCESS",
        f"Detected device: {detected['device']}",
        detected,
    )
