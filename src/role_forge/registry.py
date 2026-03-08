"""Source parsing and git operations for role-forge registry."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from role_forge.config import find_config, load_config


@dataclass
class ParsedSource:
    """A parsed source reference."""

    org: str | None = None
    repo: str | None = None
    ref: str | None = None
    local_path: str | None = None

    @property
    def is_local(self) -> bool:
        return self.local_path is not None

    @property
    def github_url(self) -> str:
        if self.is_local:
            raise ValueError("Local source has no GitHub URL")
        return f"https://github.com/{self.org}/{self.repo}"

    @property
    def cache_key(self) -> str:
        if self.is_local:
            raise ValueError("Local source has no cache key")
        return f"{self.org}/{self.repo}"


def parse_source(source: str) -> ParsedSource:
    """Parse a source string into a ParsedSource.

    Formats:
        org/repo            → GitHub repo
        org/repo@ref        → GitHub repo at ref
        ./path              → local relative path
        /path               → local absolute path
    """
    if not source:
        raise ValueError("Invalid source: empty string")

    if source.startswith("./") or source.startswith("/"):
        return ParsedSource(local_path=source)

    if "/" not in source:
        raise ValueError(f"Invalid source: {source!r}. Expected 'org/repo' or a local path.")

    # Split off @ref if present
    if "@" in source:
        repo_part, ref = source.rsplit("@", 1)
    else:
        repo_part, ref = source, None

    parts = repo_part.split("/", 1)
    return ParsedSource(org=parts[0], repo=parts[1], ref=ref)


CACHE_DIR = Path.home() / ".config" / "role-forge" / "repos"


def fetch_source(source: ParsedSource, cache_root: Path | None = None) -> Path:
    """Fetch source to local path. Returns directory containing agent definitions.

    - Local sources: validates path exists, returns it directly.
    - GitHub sources: clones/fetches to cache, returns cache path.
    """
    if source.is_local:
        assert source.local_path is not None  # narrowing for type checker
        path = Path(source.local_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Local source not found: {source.local_path}")
        return path

    cache = (cache_root or CACHE_DIR) / source.cache_key
    if (cache / ".git").is_dir():
        _git_fetch(cache, source.ref)
    else:
        _git_clone(source.github_url, cache, source.ref)

    return cache


def _git_clone(url: str, dest: Path, ref: str | None) -> None:
    """Shallow clone a repo."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", "--depth", "1"]
    if ref:
        cmd.extend(["--branch", ref])
    cmd.extend([url, str(dest)])
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _git_fetch(repo_dir: Path, ref: str | None) -> None:
    """Fetch and checkout in an existing clone."""
    subprocess.run(
        ["git", "fetch", "origin"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    target = ref or "origin/HEAD"
    subprocess.run(
        ["git", "checkout", target],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
    )


def find_roles_dir(repo_path: Path) -> Path:
    """Find agent definitions directory in a fetched repo.

    Priority:
    1. roles.toml roles_dir / agents_dir setting
    2. refit.toml roles_dir / agents_dir setting  (legacy - deprecated)
    3. roles/ directory
    """
    config_path = find_config(repo_path)
    if config_path is not None:
        roles_dir = repo_path / load_config(config_path).roles_dir
        if roles_dir.is_dir():
            return roles_dir

    # Default fallback
    roles_dir = repo_path / "roles"
    if roles_dir.is_dir():
        return roles_dir

    raise FileNotFoundError(
        f"No agent definitions found in {repo_path}. "
        "Expected 'roles.toml' (or legacy 'refit.toml') with roles_dir, or a roles/ directory."
    )
