from __future__ import annotations

from pathlib import Path
from typing import Any

PROMPTS_DIR = Path(__file__).with_name("prompts")


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


def build_system_instruction(runtime_info: dict[str, Any] | None = None) -> str:
    parts = [load_prompt("system"), load_prompt("developer"), load_prompt("schemas")]
    if runtime_info:
        parts.append("\n## Runtime Information\n\n```json\n" + _format_json(runtime_info) + "\n```\n")
    return "\n\n".join(parts)


def _format_json(value: Any) -> str:
    import json

    return json.dumps(value, indent=2, sort_keys=True, default=str)
