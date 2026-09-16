import json
from collections.abc import Callable

import pytest
from virgo_agentic_dag.api.web.mappers import transcript_mapper

pytestmark = pytest.mark.unit

ToTranscriptLine = Callable[[str, str, str | list[dict[str, object]]], str]


@pytest.fixture
def recorded_at() -> str:
    return "2026-08-15T09:00:00.000Z"


@pytest.fixture
def to_transcript_line(recorded_at: str) -> ToTranscriptLine:
    return lambda record_type, uuid, content: json.dumps(
        {
            "type": record_type,
            "uuid": uuid,
            "timestamp": recorded_at,
            "isSidechain": False,
            "message": {"role": record_type, "content": content},
        }
    )


def test_transcript_mapper_attaches_a_tool_result_to_the_tool_use_message_when_its_tool_use_id_matches_the_message_id(
    to_transcript_line: ToTranscriptLine,
) -> None:
    tool_use_block = {
        "type": "tool_use",
        "id": "toolu-1",
        "name": "Bash",
        "input": {"command": "git status"},
    }
    tool_result_block = {
        "type": "tool_result",
        "tool_use_id": "toolu-1",
        "content": "clean",
    }
    transcript_lines = [
        to_transcript_line("assistant", "assistant-1", [tool_use_block]),
        to_transcript_line("user", "user-2", [tool_result_block]),
    ]

    conversation_messages = transcript_mapper.to_conversation_message_responses(
        transcript_lines
    )

    assert [message.role for message in conversation_messages] == ["tool_use"]
    assert conversation_messages[0].tool_name == "Bash"
    assert conversation_messages[0].tool_result == "clean"


def test_transcript_mapper_skips_the_records_that_are_not_messages(
    to_transcript_line: ToTranscriptLine,
) -> None:
    thinking_block = {"type": "thinking", "thinking": "", "signature": "abc"}
    transcript_lines = [
        json.dumps({"type": "attachment", "uuid": "attachment-1"}),
        to_transcript_line("assistant", "assistant-1", [thinking_block]),
        to_transcript_line("user", "user-1", "hi"),
        to_transcript_line(
            "assistant", "assistant-2", [{"type": "text", "text": "hello"}]
        ),
    ]

    conversation_messages = transcript_mapper.to_conversation_message_responses(
        transcript_lines
    )

    assert [(message.role, message.text) for message in conversation_messages] == [
        ("user", "hi"),
        ("assistant", "hello"),
    ]
