"""Loader for canonical agent definitions (.agents/roles/*.md)."""

from __future__ import annotations

from pathlib import Path

import yaml

from agent_caster.log import logger
from agent_caster.models import AgentDef, ModelConfig


class LoadError(Exception):
    """Raised when an agent definition file cannot be parsed."""


def load_agents(agents_dir: Path, *, strict: bool = False) -> list[AgentDef]:
    """Load all agent definitions from a directory (recursively), sorted by name.

    Walks *agents_dir* recursively so that role files stored in sub-directories
    (e.g. ``roles/team-a/scout.md``) are also discovered and loaded.

    By default, files that fail to parse are skipped with a warning so that
    one malformed definition does not block the rest.  Pass ``strict=True`` to
    re-raise the first parse error instead.
    """
    if not agents_dir.is_dir():
        raise LoadError(f"Agents directory not found: {agents_dir}")

    agents = []
    for md_path in sorted(agents_dir.rglob("*.md")):
        logger.debug(f"Loading agent from {md_path.relative_to(agents_dir)}")
        try:
            agents.append(parse_agent_file(md_path))
        except LoadError as exc:
            if strict:
                raise
            logger.warning(f"Skipping {md_path.relative_to(agents_dir)}: {exc}", exc_info=True)
    logger.debug(f"Loaded {len(agents)} agent(s) from {agents_dir}")
    return agents


def parse_agent_file(md_path: Path) -> AgentDef:
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

    prompt_content = _resolve_prompt(defn, body, md_path.parent)

    return AgentDef(
        name=defn["name"],
        description=(defn.get("description", "") or "").strip(),
        role=defn.get("role", "subagent"),
        model=model,
        skills=defn.get("skills", []) or [],
        capabilities=defn.get("capabilities", []) or [],
        prompt_content=prompt_content,
        prompt_file=defn.get("prompt_file"),
        source_path=md_path.resolve(),
    )


def _split_frontmatter(text: str) -> tuple[str, str]:
    """Split YAML frontmatter from markdown body."""
    if not text.startswith("---"):
        raise LoadError("File does not start with YAML frontmatter (---)")
    try:
        end = text.index("---", 3)
    except ValueError as exc:
        raise LoadError("Missing closing --- for YAML frontmatter") from exc
    fm_text = text[3:end]
    body = text[end + 3 :].lstrip("\n")
    return fm_text, body


def _resolve_prompt(defn: dict, body: str, file_dir: Path) -> str:
    """Resolve prompt content from prompt_file or body."""
    prompt_file = defn.get("prompt_file")
    if prompt_file:
        prompt_path = (file_dir / prompt_file).resolve()
        if prompt_path.is_file():
            return prompt_path.read_text(encoding="utf-8")
        return ""
    return body
