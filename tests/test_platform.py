"""Tests for platform.py — detect AI coding tools."""

from __future__ import annotations

from agent_caster.platform import detect_platforms


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


def test_detect_none(tmp_path):
    assert detect_platforms(tmp_path) == []
