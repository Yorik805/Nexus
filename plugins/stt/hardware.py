from __future__ import annotations

from typing import Callable

from .config import load_config

SUPPORTED_DEVICES = ("cuda", "cpu")


def _probe_cuda() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except (ImportError, OSError):
        return False


def detect_hardware(
    preferred_device: str | None = None,
    probe_cuda: Callable[[], bool] | None = None,
) -> dict[str, str]:
    """Detect available STT computing hardware.

    Args:
        preferred_device: Optional override for the device preference.
        probe_cuda: Optional hook to override CUDA detection for testing.

    Returns:
        A dictionary containing the selected device.
    """
    config = load_config()
    target = str(preferred_device or config.get("preferred_device", "AUTO")).strip().upper()
    probe_cuda = probe_cuda or _probe_cuda

    if target == "AUTO":
        if probe_cuda():
            selected = "cuda"
        else:
            selected = "cpu"
    elif target == "CUDA":
        selected = "cuda" if probe_cuda() else "cpu"
    elif target == "CPU":
        selected = "cpu"
    else:
        selected = "cpu"

    if selected not in SUPPORTED_DEVICES:
        selected = "cpu"

    return {"device": selected}
