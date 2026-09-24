"""An error for a transcript cursor past the end of its file."""

from __future__ import annotations


class TranscriptCursorPastEnd(RuntimeError):
    """A runtime error for a byte offset past the end of a transcript file."""
