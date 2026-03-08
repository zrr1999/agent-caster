"""Adapter registry."""

from __future__ import annotations

from importlib.metadata import entry_points

from agent_caster.adapters.claude import ClaudeAdapter
from agent_caster.adapters.cursor import CursorAdapter
from agent_caster.adapters.opencode import OpenCodeAdapter
from agent_caster.adapters.windsurf import WindsurfAdapter
from agent_caster.models import BaseAdapter

BUILTIN_ADAPTERS: dict[str, type[BaseAdapter]] = {
    "opencode": OpenCodeAdapter,
    "claude": ClaudeAdapter,
    "cursor": CursorAdapter,
    "windsurf": WindsurfAdapter,
}


def get_adapter(name: str) -> BaseAdapter:
    """Get an adapter instance by target name."""
    adapter_cls = _all_adapters().get(name)
    if adapter_cls is None:
        raise ValueError(f"Unknown adapter: {name!r}. Available: {sorted(_all_adapters())}")
    return adapter_cls()


def list_adapters() -> list[str]:
    """Return all built-in and third-party adapter names."""
    return sorted(_all_adapters())


def _all_adapters() -> dict[str, type[BaseAdapter]]:
    adapters = dict(BUILTIN_ADAPTERS)
    for entry_point in entry_points(group="agent_caster.adapters"):
        loaded = entry_point.load()
        if isinstance(loaded, type):
            adapters.setdefault(entry_point.name, loaded)
    return adapters
