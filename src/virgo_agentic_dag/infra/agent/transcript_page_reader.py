"""A transcript reader for byte-offset pagination."""

from __future__ import annotations

import os
from pathlib import Path

from virgo_agentic_dag.config.constants import TRANSCRIPT_BLOCK_SIZE_BYTES
from virgo_agentic_dag.domain.agent.transcript_line import TranscriptLine
from virgo_agentic_dag.domain.exceptions.host.transcript_cursor_past_end import (
    TranscriptCursorPastEnd,
)
from virgo_agentic_dag.domain.infra.agent.transcript_reader import TranscriptReader


class TranscriptPageReader(TranscriptReader):
    """A transcript reader for byte-offset pagination."""

    def list_lines_before(
        self, transcript_path: Path, before: int | None
    ) -> list[TranscriptLine]:
        with transcript_path.open("rb") as transcript_file:
            file_size = transcript_file.seek(0, os.SEEK_END)
            block_end = file_size if before is None else before
            if block_end > file_size:
                raise TranscriptCursorPastEnd(
                    f"{block_end} is past the end of {transcript_path}"
                )

            block_start = block_end
            transcript_lines: list[TranscriptLine] = []
            while not transcript_lines and block_start > 0:
                block_start = max(0, block_start - TRANSCRIPT_BLOCK_SIZE_BYTES)
                transcript_file.seek(block_start)
                block = transcript_file.read(block_end - block_start)
                transcript_lines = self._list_whole_lines(block, block_start)

        return transcript_lines

    def list_lines_from(
        self, transcript_path: Path, offset: int, limit: int
    ) -> list[TranscriptLine]:
        transcript_lines: list[TranscriptLine] = []
        line_offset = offset
        with transcript_path.open("rb") as transcript_file:
            transcript_file.seek(offset)
            while len(transcript_lines) < limit:
                line = transcript_file.readline()
                is_whole_line = line.endswith(b"\n")
                if not is_whole_line:
                    break

                line_bytes = line.removesuffix(b"\n")
                text = line_bytes.decode("utf-8", errors="replace")
                transcript_line = TranscriptLine(offset=line_offset, text=text)
                transcript_lines.append(transcript_line)
                line_offset += len(line)

        return transcript_lines

    def _list_whole_lines(self, block: bytes, block_start: int) -> list[TranscriptLine]:
        """Return complete lines from the byte block, or an empty list when the block contains no complete line."""
        first_line_start = 0 if block_start == 0 else block.find(b"\n") + 1
        last_line_end = block.rfind(b"\n")
        if last_line_end < first_line_start:
            return []

        whole_lines = block[first_line_start:last_line_end].split(b"\n")
        transcript_lines: list[TranscriptLine] = []
        line_offset = block_start + first_line_start
        for line in whole_lines:
            text = line.decode("utf-8", errors="replace")
            transcript_line = TranscriptLine(offset=line_offset, text=text)
            transcript_lines.append(transcript_line)
            line_offset += len(line) + len(b"\n")

        return transcript_lines
