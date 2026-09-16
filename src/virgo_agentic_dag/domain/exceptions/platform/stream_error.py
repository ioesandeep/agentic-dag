"""The error raised when the event stream cannot be opened or dies mid-read."""

from __future__ import annotations


class StreamError(RuntimeError):
    """Raised when the SSE connection fails to open or is lost."""
