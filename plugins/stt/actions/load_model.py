from __future__ import annotations

from ..model_loader import load_model
from ..stt_helpers import build_response


def load_model_action(data: dict) -> dict:
    if not isinstance(data, dict):
        return build_response("ERROR", "LOAD_MODEL requires a dictionary payload.")

    config = data.get("config") if isinstance(data.get("config"), dict) else None
    try:
        model = load_model(config)
    except Exception as exc:  # pragma: no cover
        return build_response(
            "ERROR",
            f"Failed to load STT model: {exc}",
        )

    return build_response(
        "SUCCESS",
        "STT model loaded successfully.",
        model.to_dict(),
    )
