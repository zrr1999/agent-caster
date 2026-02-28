"""Adapter registry."""

from __future__ import annotations

from agent_caster.adapters.claude import ClaudeAdapter
from agent_caster.adapters.opencode import OpenCodeAdapter

BUILTIN_ADAPTERS: dict[str, type] = {
    "opencode": OpenCodeAdapter,
    "claude": ClaudeAdapter,
}


def get_adapter(name: str):
    """Get an adapter instance by target name."""
    adapter_cls = BUILTIN_ADAPTERS.get(name)
    if adapter_cls is None:
        raise ValueError(f"Unknown adapter: {name!r}. Available: {list(BUILTIN_ADAPTERS)}")
    return adapter_cls()
