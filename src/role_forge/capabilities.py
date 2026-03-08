"""Centralized capability expansion for canonical role definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from role_forge.groups import ALL_TOOL_IDS, BASH_POLICIES, TOOL_GROUPS

CapabilityValue = str | dict[str, Any]


@dataclass(frozen=True)
class CapabilitySpec:
    """Expanded, platform-agnostic capability result for one role."""

    tool_ids: tuple[str, ...] = ()
    bash_patterns: tuple[str, ...] = ()
    delegates: tuple[str, ...] = ()
    full_access: bool = False

    def tool_flags(self) -> dict[str, bool]:
        """Return tool ids as a stable bool map for adapters that need flags."""
        return dict.fromkeys(self.tool_ids, True)


def expand_capabilities(
    capabilities: list[CapabilityValue],
    capability_map: dict[str, dict[str, bool]],
) -> CapabilitySpec:
    """Expand raw capabilities into a canonical intermediate representation."""
    tool_ids: list[str] = []
    bash_patterns: list[str] = []
    delegates: list[str] = []
    full_access = False

    for cap in capabilities:
        if isinstance(cap, str):
            if cap == "all":
                full_access = True
                tool_ids.extend(ALL_TOOL_IDS)
            elif cap in BASH_POLICIES:
                tool_ids.append("bash")
                bash_patterns.extend(BASH_POLICIES[cap])
            elif cap in TOOL_GROUPS:
                tool_ids.extend(TOOL_GROUPS[cap])
            elif cap in capability_map:
                tool_ids.extend(
                    tool_id for tool_id, enabled in capability_map[cap].items() if enabled
                )
            else:
                tool_ids.append(cap)
            continue

        if not isinstance(cap, dict):
            continue

        if "bash" in cap:
            patterns = cap["bash"] or []
            tool_ids.append("bash")
            bash_patterns.extend(patterns)

        if "delegate" in cap:
            refs = cap["delegate"] or []
            if refs:
                tool_ids.append("task")
                delegates.extend(refs)

    return CapabilitySpec(
        tool_ids=tuple(_dedupe(tool_ids)),
        bash_patterns=tuple(_dedupe(bash_patterns)),
        delegates=tuple(_dedupe(delegates)),
        full_access=full_access,
    )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped
