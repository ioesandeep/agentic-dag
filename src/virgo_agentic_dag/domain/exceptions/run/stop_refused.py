"""The runtime error for a node stop that fails."""

from __future__ import annotations


class StopRefused(RuntimeError):
    """An error raised when the run has no such node, the node is not in progress, or its session is not running."""
