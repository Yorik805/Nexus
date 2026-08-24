from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from plugins.stt.hardware import detect_hardware
from plugins.stt.model_loader import get_current_device, get_loaded_model, load_model, unload_model


def setup_function() -> None:
    unload_model()


def test_detect_hardware_prefers_gpu_when_available() -> None:
    result = detect_hardware(probe_cuda=lambda: True)
    assert result["device"] == "cuda"


def test_detect_hardware_cpu_fallback() -> None:
    result = detect_hardware(probe_cuda=lambda: False)
    assert result["device"] == "cpu"


def test_load_model_only_loads_once() -> None:
    first_model = load_model()
    second_model = load_model()

    assert first_model is second_model
    assert first_model.model_name == "nexus/stt-base"


def test_repeated_get_loaded_model_returns_same_instance() -> None:
    model = load_model()
    assert get_loaded_model() is model


def test_unload_model_frees_resources() -> None:
    load_model()
    assert unload_model() is True
    assert get_loaded_model() is None
    assert get_current_device() is None
