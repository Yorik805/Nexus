"""Shared Nexus host and port configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).with_name("nexus.config.json")


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as stream:
        config = json.load(stream)
    if not isinstance(config, dict) or not isinstance(config.get("host"), str):
        raise ValueError(f"Invalid Nexus configuration: {CONFIG_PATH}")
    return config


def host_url(config: dict[str, Any] | None = None, port_key: str = "runtime_port") -> str:
    values = config or load_config()
    protocol = str(values.get("protocol", "http"))
    host = str(values["host"])
    port = int(values[port_key])
    return f"{protocol}://{host}:{port}"


def config_value(name: str, default: Any) -> Any:
    return load_config().get(name, default)
