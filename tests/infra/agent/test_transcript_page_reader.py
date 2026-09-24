from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.domain.agent.transcript_line import TranscriptLine
from virgo_agentic_dag.domain.exceptions.host.transcript_cursor_past_end import (
    TranscriptCursorPastEnd,
)
from virgo_agentic_dag.infra.agent.transcript_page_reader import TranscriptPageReader

pytestmark = pytest.mark.integration

SMALL_BLOCK_SIZE_BYTES = 16


@pytest.fixture
def transcript_path(tmp_path: Path) -> Path:
    return tmp_path / "token-seed.jsonl"


def test_transcript_page_reader_returns_each_complete_line_once_when_block_offsets_progress_to_the_start_of_the_file(
    mocker: MockerFixture, transcript_path: Path
) -> None:
    mocker.patch(
        "virgo_agentic_dag.infra.agent.transcript_page_reader.TRANSCRIPT_BLOCK_SIZE_BYTES",
        SMALL_BLOCK_SIZE_BYTES,
    )
    transcript_path.write_bytes(
        b'{"n": 0}\n\n{"n": 2, "text": "a line past one block"}\n{"n": 3}\n{"n": 4'
    )
    reader = TranscriptPageReader()

    transcript_lines: list[TranscriptLine] = []
    block_lines = reader.list_lines_before(transcript_path, None)
    while block_lines:
        transcript_lines = block_lines + transcript_lines
        block_lines = reader.list_lines_before(transcript_path, block_lines[0].offset)

    assert transcript_lines == [
        TranscriptLine(offset=0, text='{"n": 0}'),
        TranscriptLine(offset=9, text=""),
        TranscriptLine(offset=10, text='{"n": 2, "text": "a line past one block"}'),
        TranscriptLine(offset=52, text='{"n": 3}'),
    ]


def test_transcript_page_reader_returns_no_lines_when_the_cursor_is_at_the_start_of_the_file(
    transcript_path: Path,
) -> None:
    transcript_path.write_bytes(b'{"n": 0}\n')

    transcript_lines = TranscriptPageReader().list_lines_before(transcript_path, 0)

    assert transcript_lines == []


def test_transcript_page_reader_raises_transcript_cursor_past_end_when_the_cursor_is_past_the_end_of_the_file(
    transcript_path: Path,
) -> None:
    transcript_path.write_bytes(b'{"n": 0}\n')

    with pytest.raises(TranscriptCursorPastEnd, match="10 is past the end"):
        TranscriptPageReader().list_lines_before(transcript_path, 10)
