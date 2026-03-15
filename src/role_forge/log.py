"""Logging configuration using loguru."""

from __future__ import annotations

import sys

from loguru import logger


def _stdout_sink(message: str) -> None:
    """Dynamic sink that always resolves to the current sys.stdout."""
    sys.stdout.write(message)
    sys.stdout.flush()


# Remove loguru's default handler (stderr with DEBUG level)
logger.remove()

# Add stdout handler for INFO+ (matches original print() behaviour for CLI output).
# Using a callable sink so that stdout redirection (e.g. Typer CliRunner) is respected.
logger.add(
    _stdout_sink,
    level="INFO",
    format="{message}",
    colorize=True,
)

__all__ = ["logger"]
