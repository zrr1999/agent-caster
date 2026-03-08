"""Static capability group and bash policy definitions."""

from __future__ import annotations

# -- Tool groups ---------------------------------------------------------------
# Keys are capability group names used in canonical agent definitions.
# Values are lists of semantic tool identifiers (adapter translates to platform names).

TOOL_GROUPS: dict[str, list[str]] = {
    # Primary groups
    "basic": ["read", "glob", "grep", "write", "edit", "webfetch", "websearch"],
    "read": ["read", "glob", "grep"],
    "write": ["write", "edit"],
    "web-access": ["webfetch", "websearch"],
    "delegate": ["task"],
}

ALL_TOOL_IDS: list[str] = [
    "read",
    "glob",
    "grep",
    "write",
    "edit",
    "webfetch",
    "websearch",
    "bash",
    "task",
]

# -- Bash policies -------------------------------------------------------------
# Each policy is a list of glob patterns for allowed bash commands.
# Pattern convention: "cmd*" matches both bare command and command with arguments.

SAFE_BASH_PATTERNS: list[str] = [
    # Output / text processing
    "echo*",
    "printf*",
    "wc*",
    "sort*",
    "uniq*",
    "head*",
    "tail*",
    "cut*",
    "tr*",
    "diff*",
    # Path helpers
    "pwd",
    "basename*",
    "dirname*",
    # System info
    "date*",
    "uname*",
    "whoami",
    "which*",
    # Git read operations
    "git log*",
    "git diff*",
    "git status*",
    "git branch*",
    "git show*",
    "git rev-parse*",
    "git remote*",
]

BASH_POLICIES: dict[str, list[str]] = {
    "safe-bash": SAFE_BASH_PATTERNS,
}
