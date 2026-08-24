from __future__ import annotations

from ..model_loader import get_loaded_model
from ..stt_helpers import build_response


def get_model_action(data: dict) -> dict:
    if not isinstance(data, dict):
        return build_response("ERROR", "GET_MODEL requires a dictionary payload.")

    model = get_loaded_model()
    if model is None:
        return build_response("ERROR", "No STT model is currently loaded.")

    return build_response(
        "SUCCESS",
        "STT model is loaded.",
        model.to_dict(),
    )
