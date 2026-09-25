"""The error raised when the dagctl command of a node action fails."""

from __future__ import annotations


class NodeActionFailed(RuntimeError):
    """Raised when a dagctl node action exits with an unexpected code."""
