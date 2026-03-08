from __future__ import annotations

import sys


def main() -> None:
    command = " ".join(sys.argv[1:]).strip()
    hint = f"role-forge {command}".strip()
    print("`agent-caster` has been renamed to `role-forge`.")
    print(f"Please use `{hint}` instead.")
    raise SystemExit(1)
