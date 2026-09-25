"""The error raised when a retry, wake, or stop of a node is refused."""

from __future__ import annotations


class NodeActionRefused(RuntimeError):
    """Raised when another command has the run lock, a woken node is not resting, or dagctl refuses the node."""
