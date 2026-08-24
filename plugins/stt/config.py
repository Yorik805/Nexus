from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_STT_CONFIG: dict[str, Any] = {
    "preferred_device": "AUTO",
    "model_name": "nexus/stt-base",
    "compute_type": "float16",
    "language": "en",
    "beam_size": 5,
    "vad_enabled": False,
    "max_audio_length_seconds": 30,
    "sample_rate": 16000,
}

CONFIG_FILE_PATH = Path(__file__).parent / "config.json"


def _load_json_config(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return {}
        return data
    except (OSError, json.JSONDecodeError):
        return {}


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load STT configuration from disk and merge with defaults."""
    config_path = Path(path) if path else CONFIG_FILE_PATH
    config = DEFAULT_STT_CONFIG.copy()

    if config_path.exists():
        json_data = _load_json_config(config_path)
        for key, value in json_data.items():
            if key in config:
                config[key] = value

    return config


def get_config_value(key: str, default: Any = None) -> Any:
    config = load_config()
    return config.get(key, default)
