from __future__ import annotations

from ..model_loader import unload_model
from ..stt_helpers import build_response


def unload_model_action(data: dict) -> dict:
    if not isinstance(data, dict):
        return build_response("ERROR", "UNLOAD_MODEL requires a dictionary payload.")

    unloaded = unload_model()
    if not unloaded:
        return build_response("ERROR", "No STT model was loaded.")

    return build_response("SUCCESS", "STT model unloaded successfully.")
