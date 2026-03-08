"""Tests for centralized capability expansion."""

from __future__ import annotations

from role_forge.capabilities import expand_capabilities
from role_forge.groups import SAFE_BASH_PATTERNS


def test_expand_read_group() -> None:
    spec = expand_capabilities(["read"], {})
    assert spec.tool_ids == ("read", "glob", "grep")
    assert spec.bash_patterns == ()
    assert spec.delegates == ()
    assert spec.full_access is False


def test_expand_safe_bash_policy() -> None:
    spec = expand_capabilities(["safe-bash"], {})
    assert spec.tool_ids == ("bash",)
    assert spec.bash_patterns == tuple(SAFE_BASH_PATTERNS)


def test_expand_bash_merges_and_dedupes() -> None:
    spec = expand_capabilities(
        ["safe-bash", {"bash": ["git diff*", "custom cmd*", "git diff*"]}],
        {},
    )
    assert spec.tool_ids == ("bash",)
    assert "custom cmd*" in spec.bash_patterns
    assert spec.bash_patterns.count("git diff*") == 1


def test_expand_delegate_collects_targets() -> None:
    spec = expand_capabilities(
        [{"delegate": ["nested/worker", "nested/reviewer", "nested/worker"]}],
        {},
    )
    assert spec.tool_ids == ("task",)
    assert spec.delegates == ("nested/worker", "nested/reviewer")


def test_expand_all_sets_full_access() -> None:
    spec = expand_capabilities(["all"], {})
    assert spec.full_access is True
    assert spec.tool_ids == (
        "read",
        "glob",
        "grep",
        "write",
        "edit",
        "webfetch",
        "websearch",
        "bash",
        "task",
    )


def test_expand_capability_map_flags() -> None:
    spec = expand_capabilities(["context7"], {"context7": {"context7": True, "unused": False}})
    assert spec.tool_ids == ("context7",)


def test_expand_legacy_aliases() -> None:
    spec = expand_capabilities(["read-code", "write-code"], {})
    assert spec.tool_ids == ("read", "glob", "grep", "write", "edit")
