from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version


def _resolve_version() -> str:
    try:
        return package_version("role-forge")
    except PackageNotFoundError:
        return "0.0.1"


__version__ = _resolve_version()
__version_tuple__ = tuple(__version__.split("."))

__all__ = ["__version__", "__version_tuple__"]
