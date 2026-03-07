"""Platform-agnostic capability group and bash policy definitions.

Tool groups map abstract capability names to semantic tool identifiers.
Bash policies map policy names to lists of allowed command patterns.
Adapters translate these into platform-specific tool names and formats.
"""

from __future__ import annotations

# -- Tool groups ---------------------------------------------------------------
# Keys are capability group names used in canonical agent definitions.
# Values are lists of semantic tool identifiers (adapter translates to platform names).

TOOL_GROUPS: dict[str, list[str]] = {
    "read": ["read", "glob", "grep"],
    "write": ["write", "edit"],
    "write-report": ["write"],
    "web-read": ["webfetch"],
    "web-access": ["webfetch", "websearch"],
}

# -- Bash policies -------------------------------------------------------------
# Each policy is a list of glob patterns for allowed bash commands.
# Pattern convention: "cmd*" matches both bare command and command with arguments.
# readonly-bash is a strict superset of safe-bash.

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

READONLY_BASH_EXTRA: list[str] = [
    # File reading
    "cat*",
    "less*",
    # File/directory listing & search
    "ls*",
    "find*",
    "tree*",
    # Content search
    "grep*",
    "rg*",
    "ag*",
    # File metadata
    "file*",
    "stat*",
    # Disk / system
    "du*",
    "df*",
    "env",
    "printenv*",
    "ps*",
    # Package managers (read-only)
    "pip list*",
    "pip show*",
    "npm list*",
    "cargo metadata*",
]

BASH_POLICIES: dict[str, list[str]] = {
    "safe-bash": SAFE_BASH_PATTERNS,
    "readonly-bash": SAFE_BASH_PATTERNS + READONLY_BASH_EXTRA,
}
