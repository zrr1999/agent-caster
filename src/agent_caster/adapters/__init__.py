"""Adapter registry."""

from __future__ import annotations

from agent_caster.adapters.claude import ClaudeAdapter
from agent_caster.adapters.cursor import CursorAdapter
from agent_caster.adapters.opencode import OpenCodeAdapter
from agent_caster.models import BaseAdapter

BUILTIN_ADAPTERS: dict[str, type[BaseAdapter]] = {
    "opencode": OpenCodeAdapter,
    "claude": ClaudeAdapter,
    "cursor": CursorAdapter,
}


def get_adapter(name: str) -> BaseAdapter:
    """Get an adapter instance by target name."""
    adapter_cls = BUILTIN_ADAPTERS.get(name)
    if adapter_cls is None:
        raise ValueError(f"Unknown adapter: {name!r}. Available: {list(BUILTIN_ADAPTERS)}")
    return adapter_cls()
