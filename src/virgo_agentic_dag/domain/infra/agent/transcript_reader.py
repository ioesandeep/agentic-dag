"""An interface for listing transcript lines by byte offset."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from virgo_agentic_dag.domain.agent.transcript_line import TranscriptLine


class TranscriptReader(ABC):
    """An interface for listing transcript lines by byte offset."""

    @abstractmethod
    def list_lines_before(
        self, transcript_path: Path, before: int | None
    ) -> list[TranscriptLine]:
        """Return the oldest-first block of complete transcript lines ending before the byte offset, using the end of the file when the offset is None, or an empty list when no complete line ends before that position."""

    @abstractmethod
    def list_lines_from(
        self, transcript_path: Path, offset: int, limit: int
    ) -> list[TranscriptLine]:
        """Return up to `limit` complete transcript lines from `offset`, or an empty list when no complete transcript line exists from that offset."""
