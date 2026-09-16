"""The error raised when a git worktree cannot be created or removed."""

from __future__ import annotations


class WorktreeError(RuntimeError):
    """Raised when git refuses to create or remove an attempt worktree."""
