"""Source parsing and git operations for role-forge registry."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

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
        if self.ref:
            return f"{self.org}/{self.repo}@{self.ref}"
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
    _ensure_head_checked_out(dest, ref)


def _git_fetch(repo_dir: Path, ref: str | None) -> None:
    """Fetch and checkout in an existing clone (update cache to latest remote)."""
    subprocess.run(
        ["git", "fetch", "origin"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    _ensure_head_checked_out(repo_dir, ref)
    # For default branch (no explicit ref), fast-forward local branch to origin.
    # This keeps the cached repo up to date between role-forge runs.
    if ref is None:
        result = subprocess.run(
            ["git", "pull", "--ff-only", "origin"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        stdout = (result.stdout or "").strip()
        # Only log when the pull actually updated something (not "Already up to date.").
        if stdout and "Already up to date" not in stdout:
            logger.info(f"  • updated source cache from origin: {repo_dir}")


def _ensure_head_checked_out(repo_dir: Path, ref: str | None) -> None:
    """Ensure the working tree has a checked out commit after clone/fetch."""
    if ref:
        target = ref
    else:
        result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            cwd=repo_dir,
            check=False,
            capture_output=True,
            text=True,
        )
        target = (
            result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else "main"
        )

    has_refs = subprocess.run(
        ["git", "show-ref", "--verify", f"refs/heads/{target}"],
        cwd=repo_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    if has_refs.returncode != 0 and target == "main":
        has_master = subprocess.run(
            ["git", "show-ref", "--verify", "refs/heads/master"],
            cwd=repo_dir,
            check=False,
            capture_output=True,
            text=True,
        )
        if has_master.returncode == 0:
            target = "master"

    if (
        subprocess.run(
            ["git", "show-ref"],
            cwd=repo_dir,
            check=False,
            capture_output=True,
            text=True,
        ).returncode
        != 0
    ):
        return

    checkout_targets = [target]
    if target == "main":
        checkout_targets.append("master")

    last_error: subprocess.CalledProcessError | None = None
    for candidate in checkout_targets:
        try:
            subprocess.run(
                ["git", "checkout", candidate],
                cwd=repo_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            return
        except subprocess.CalledProcessError as exc:
            last_error = exc

    assert last_error is not None
    raise subprocess.CalledProcessError(
        returncode=last_error.returncode,
        cmd=last_error.cmd,
        output=last_error.output,
        stderr=(last_error.stderr or "").strip()
        or "Could not determine a usable default branch after fetching the repository.",
    )


def find_roles_dir(repo_path: Path) -> Path:
    """Find agent definitions directory in a fetched source repo.

    Priority:
    1. roles.toml [project].roles_dir setting
    2. .agents/roles/ directory (default install layout)
    3. roles/ directory (legacy/simple layout)
    """
    config_path = find_config(repo_path)
    if config_path is not None:
        roles_dir = repo_path / load_config(config_path).roles_dir
        if roles_dir.is_dir():
            return roles_dir

    roles_dir = repo_path / ".agents" / "roles"
    if roles_dir.is_dir():
        return roles_dir

    # Legacy fallback
    roles_dir = repo_path / "roles"
    if roles_dir.is_dir():
        return roles_dir

    raise FileNotFoundError(
        f"No agent definitions found in {repo_path}. "
        "Expected '.agents/roles/' or 'roles/' directory."
    )
