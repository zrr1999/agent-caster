"""Tests for platform.py — detect AI coding tools."""

from __future__ import annotations

from role_forge.platform import detect_platforms, resolve_targets


def test_detect_claude_by_dir(tmp_path):
    (tmp_path / ".claude").mkdir()
    assert "claude" in detect_platforms(tmp_path)


def test_detect_claude_by_claude_md(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("# Claude")
    assert "claude" in detect_platforms(tmp_path)


def test_detect_opencode_by_dir(tmp_path):
    (tmp_path / ".opencode").mkdir()
    assert "opencode" in detect_platforms(tmp_path)


def test_detect_opencode_by_json(tmp_path):
    (tmp_path / "opencode.json").write_text("{}")
    assert "opencode" in detect_platforms(tmp_path)


def test_detect_cursor_by_dir(tmp_path):
    (tmp_path / ".cursor").mkdir()
    assert "cursor" in detect_platforms(tmp_path)


def test_detect_cursor_by_cursorrules(tmp_path):
    (tmp_path / ".cursorrules").write_text("# Cursor rules")
    assert "cursor" in detect_platforms(tmp_path)


def test_detect_multiple(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".opencode").mkdir()
    platforms = detect_platforms(tmp_path)
    assert "claude" in platforms
    assert "opencode" in platforms


def test_detect_all_three(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".opencode").mkdir()
    (tmp_path / ".cursor").mkdir()
    platforms = detect_platforms(tmp_path)
    assert "claude" in platforms
    assert "opencode" in platforms
    assert "cursor" in platforms


def test_detect_windsurf_by_dir(tmp_path):
    (tmp_path / ".windsurf").mkdir()
    assert "windsurf" in detect_platforms(tmp_path)


def test_detect_windsurf_by_windsurfrules(tmp_path):
    (tmp_path / ".windsurfrules").write_text("# Windsurf rules")
    assert "windsurf" in detect_platforms(tmp_path)


def test_detect_copilot_by_instructions(tmp_path):
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "copilot-instructions.md").write_text("# Instructions")
    assert "copilot" in detect_platforms(tmp_path)


def test_detect_copilot_by_agents_dir(tmp_path):
    (tmp_path / ".github" / "agents").mkdir(parents=True)
    assert "copilot" in detect_platforms(tmp_path)


def test_detect_all_four(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".opencode").mkdir()
    (tmp_path / ".cursor").mkdir()
    (tmp_path / ".windsurf").mkdir()
    platforms = detect_platforms(tmp_path)
    assert "claude" in platforms
    assert "opencode" in platforms
    assert "cursor" in platforms
    assert "windsurf" in platforms


def test_detect_all_five(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".opencode").mkdir()
    (tmp_path / ".github" / "agents").mkdir(parents=True)
    (tmp_path / ".cursor").mkdir()
    (tmp_path / ".windsurf").mkdir()
    platforms = detect_platforms(tmp_path)
    assert "claude" in platforms
    assert "opencode" in platforms
    assert "copilot" in platforms
    assert "cursor" in platforms
    assert "windsurf" in platforms


def test_detect_none(tmp_path):
    assert detect_platforms(tmp_path) == []


# -- resolve_targets -----------------------------------------------------------


def test_resolve_targets_prefers_roles_toml(tmp_path):
    """When roles.toml defines targets, use those instead of filesystem detection."""
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".opencode").mkdir()
    (tmp_path / ".cursor").mkdir()
    (tmp_path / "roles.toml").write_text(
        "[targets.opencode]\n"
        "enabled = true\n"
        "[targets.opencode.model_map]\n"
        'reasoning = "r"\ncoding = "c"\n'
        "[targets.claude]\n"
        "enabled = true\n"
        "[targets.claude.model_map]\n"
        'reasoning = "r"\ncoding = "c"\n'
    )
    targets = resolve_targets(tmp_path)
    assert sorted(targets) == ["claude", "opencode"]


def test_resolve_targets_respects_enabled_false(tmp_path):
    """Targets with enabled = false should be excluded."""
    (tmp_path / "roles.toml").write_text(
        "[targets.opencode]\n"
        "enabled = true\n"
        "[targets.opencode.model_map]\n"
        'reasoning = "r"\ncoding = "c"\n'
        "[targets.claude]\n"
        "enabled = false\n"
        "[targets.claude.model_map]\n"
        'reasoning = "r"\ncoding = "c"\n'
    )
    targets = resolve_targets(tmp_path)
    assert targets == ["opencode"]


def test_resolve_targets_falls_back_to_detection(tmp_path):
    """When no roles.toml exists, fall back to filesystem detection."""
    (tmp_path / ".claude").mkdir()
    targets = resolve_targets(tmp_path)
    assert targets == ["claude"]


def test_resolve_targets_falls_back_when_no_targets_in_config(tmp_path):
    """When roles.toml exists but has no [targets.*], fall back to detection."""
    (tmp_path / ".claude").mkdir()
    (tmp_path / "roles.toml").write_text('[project]\nroles_dir = "roles"\n')
    targets = resolve_targets(tmp_path)
    assert targets == ["claude"]


def test_resolve_targets_falls_back_when_all_disabled(tmp_path):
    """When all configured targets are disabled, fall back to detection."""
    (tmp_path / ".opencode").mkdir()
    (tmp_path / "roles.toml").write_text(
        "[targets.claude]\n"
        "enabled = false\n"
        "[targets.claude.model_map]\n"
        'reasoning = "r"\ncoding = "c"\n'
    )
    targets = resolve_targets(tmp_path)
    assert targets == ["opencode"]
