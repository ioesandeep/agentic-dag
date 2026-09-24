"""A transcript line with its byte offset."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptLine:
    """A transcript line and its byte offset."""

    offset: int  # The line's starting byte offset in the transcript file.
    text: str
