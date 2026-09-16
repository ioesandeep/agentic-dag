"""The error raised when a node cannot be skipped."""

from __future__ import annotations


class SkipRefused(RuntimeError):
    """Raised when the run has no such node, or the node is in progress or has merged."""
