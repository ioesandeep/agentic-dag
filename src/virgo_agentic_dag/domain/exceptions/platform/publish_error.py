"""The error raised when a git or platform publishing step fails."""

from __future__ import annotations


class PublishError(RuntimeError):
    """Raised when committing, pushing, or opening a pull request fails."""
