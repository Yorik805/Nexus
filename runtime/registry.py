from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any, Callable


@dataclass(frozen=True)
class PluginMetadata:
    name: str
    actions: frozenset[str]
    entry_point: Callable[[dict[str, Any]], dict[str, Any]]
    description: str = ""
    version: str | None = None


class PluginRegistry:
    """Registry of plugin entry points and actions discovered from modules."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginMetadata] = {}
        self.register_module("memory", "plugins.memory")
        self.register_module("filesystem", "plugins.filesystem")
        self.register_module("terminal", "plugins.terminal")

    def register_module(self, name: str, module_name: str) -> PluginMetadata:
        module = import_module(module_name)
        entry_point = getattr(module, "execute", None)
        if not callable(entry_point):
            raise ValueError(f"Plugin {name!r} does not expose callable execute().")
        actions = getattr(module, "_SUPPORTED_ACTIONS", None)
        if not isinstance(actions, dict):
            execute_module = import_module(f"{module_name}.execute")
            actions = getattr(execute_module, "_SUPPORTED_ACTIONS", {})
        metadata = PluginMetadata(
            name=str(name).lower(),
            actions=frozenset(str(action).upper() for action in actions),
            entry_point=entry_point,
            description=str(getattr(module, "__doc__", "") or "").splitlines()[0] if getattr(module, "__doc__", None) else "",
            version=getattr(module, "__version__", None),
        )
        self._plugins[metadata.name] = metadata
        return metadata

    def register(self, name: str, handler: Callable[[dict[str, Any]], dict[str, Any]], actions: set[str] | frozenset[str]) -> PluginMetadata:
        metadata = PluginMetadata(str(name).lower(), frozenset(str(action).upper() for action in actions), handler)
        self._plugins[metadata.name] = metadata
        return metadata

    def get(self, name: str) -> PluginMetadata | None:
        return self._plugins.get(str(name).lower())

    def get_plugin(self, name: str) -> Callable[[dict[str, Any]], dict[str, Any]] | None:
        metadata = self.get(name)
        return metadata.entry_point if metadata else None

    def list_plugins(self) -> list[str]:
        return sorted(self._plugins)

    def metadata(self) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "name": plugin.name,
                "actions": sorted(plugin.actions),
                "entry_point": f"{plugin.entry_point.__module__}.{plugin.entry_point.__name__}",
                "description": plugin.description,
                "version": plugin.version,
            }
            for name, plugin in sorted(self._plugins.items())
        }
