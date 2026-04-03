"""Loader for canonical agent definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from loguru import logger
from pydantic import ValidationError

from role_forge.models import AgentDef, HierarchyConfig, ModelConfig


class LoadError(Exception):
    """Raised when an agent definition file cannot be parsed."""


@dataclass(frozen=True)
class UnmanagedFileIssue:
    """A file under a roles directory that role-forge does not manage."""

    path: Path
    reason: str


def load_agents(roles_dir: Path, *, strict: bool = False) -> list[AgentDef]:
    """Load all agent definitions from a directory (recursively), sorted by name.

    Walks *roles_dir* recursively so that role files stored in sub-directories
    (e.g. ``roles/team-a/scout.md``) are also discovered and loaded.

    By default, files that fail to parse are skipped with a warning so that
    one malformed definition does not block the rest.  Pass ``strict=True`` to
    re-raise the first parse error instead.
    """
    if not roles_dir.is_dir():
        raise LoadError(f"Agents directory not found: {roles_dir}")

    agents = []
    for md_path in sorted(roles_dir.rglob("*.md")):
        logger.debug(f"Loading agent from {md_path.relative_to(roles_dir)}")
        try:
            agents.append(parse_agent_file(md_path, roles_dir=roles_dir))
        except LoadError as exc:
            if strict:
                raise LoadError(f"{md_path.relative_to(roles_dir)}: {exc}") from exc
            logger.warning(f"Skipping {md_path.relative_to(roles_dir)}: {exc}", exc_info=True)
    logger.debug(f"Loaded {len(agents)} agent(s) from {roles_dir}")
    return agents


def find_unmanaged_files(roles_dir: Path) -> list[UnmanagedFileIssue]:
    """Return non-markdown and invalid markdown files under a roles directory."""
    if not roles_dir.is_dir():
        return []

    issues: list[UnmanagedFileIssue] = []
    for path in sorted(roles_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix != ".md":
            issues.append(UnmanagedFileIssue(path=path, reason="Non-Markdown file"))
            continue
        try:
            parse_agent_file(path, roles_dir=roles_dir)
        except LoadError as exc:
            issues.append(UnmanagedFileIssue(path=path, reason=str(exc)))
    return issues


def parse_agent_file(md_path: Path, *, roles_dir: Path | None = None) -> AgentDef:
    """Parse a single agent definition file."""
    text = md_path.read_text(encoding="utf-8")
    fm_text, body = _split_frontmatter(text)

    defn = yaml.safe_load(fm_text)
    if not defn or not isinstance(defn, dict):
        raise LoadError(f"Empty or invalid frontmatter in {md_path}")
    if "name" not in defn:
        raise LoadError(f"Missing required 'name' field in {md_path}")

    raw_model = defn.get("model", {}) or {}
    model = ModelConfig(
        tier=raw_model.get("tier", "reasoning"),
        temperature=raw_model.get("temperature"),
    )
    hierarchy = _parse_hierarchy(defn)

    prompt_content = _resolve_prompt(defn, body, md_path.parent)
    relative_path = (
        md_path.resolve().relative_to(roles_dir.resolve()).as_posix()
        if roles_dir is not None
        else md_path.name
    )

    try:
        return AgentDef(
            name=defn["name"],
            description=(defn.get("description", "") or "").strip(),
            role=defn.get("role", "subagent"),
            model=model,
            skills=defn.get("skills", []) or [],
            capabilities=defn.get("capabilities", []) or [],
            hierarchy=hierarchy,
            prompt_content=prompt_content,
            prompt_file=defn.get("prompt_file"),
            source_path=md_path.resolve(),
            relative_path=relative_path,
        )
    except ValidationError as exc:
        raise LoadError(f"Invalid agent metadata in {md_path}: {exc}") from exc


def _split_frontmatter(text: str) -> tuple[str, str]:
    """Split YAML frontmatter from markdown body."""
    if not text.startswith("---\n") and text != "---":
        raise LoadError("File does not start with YAML frontmatter (---)")
    lines = text.splitlines(keepends=True)
    end_index: int | None = None
    for idx, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = idx
            break
    if end_index is None:
        raise LoadError("Missing closing --- for YAML frontmatter")
    fm_text = "".join(lines[1:end_index])
    body = "".join(lines[end_index + 1 :]).lstrip("\n")
    return fm_text, body


def _resolve_prompt(defn: dict, body: str, file_dir: Path) -> str:
    """Resolve prompt content from prompt_file or body."""
    prompt_file = defn.get("prompt_file")
    if prompt_file:
        prompt_path = (file_dir / prompt_file).resolve()
        if not prompt_path.is_file():
            raise LoadError(f"Referenced prompt_file does not exist: {prompt_file}")
        return prompt_path.read_text(encoding="utf-8")
    return body


def _parse_hierarchy(defn: dict) -> HierarchyConfig:
    """Parse first-class hierarchy metadata from top-level or nested keys."""
    raw_hierarchy = defn.get("hierarchy", {}) or {}
    if raw_hierarchy and not isinstance(raw_hierarchy, dict):
        raise LoadError("Field 'hierarchy' must be a mapping when provided")

    merged = dict(raw_hierarchy)
    for key in (
        "level",
        "class",
        "scheduled",
        "callable",
        "max_delegate_depth",
        "allowed_children",
    ):
        if key in defn:
            merged[key] = defn[key]

    try:
        return HierarchyConfig.model_validate(merged)
    except ValidationError as exc:
        raise LoadError(f"Invalid hierarchy metadata: {exc}") from exc
