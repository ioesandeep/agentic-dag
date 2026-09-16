import json

import pytest
from virgo_agentic_dag.api.web.mappers.codex_transcript_mapper import (
    to_conversation_message_responses,
)

pytestmark = pytest.mark.unit

TIMESTAMP = "2026-09-12T00:00:00+00:00"


def test_maps_a_command_execution_to_a_single_tool_message_when_start_and_completion_events_are_present() -> (
    None
):
    lines = [
        json.dumps(
            {
                "type": event_type,
                "timestamp": TIMESTAMP,
                "execution_id": "turn-1",
                "item": {
                    "id": "item_0",
                    "type": "command_execution",
                    "command": "pytest",
                    "status": status,
                    "aggregated_output": output,
                    "exit_code": exit_code,
                },
            }
        )
        for event_type, status, output, exit_code in [
            ("item.started", "in_progress", "", None),
            ("item.completed", "completed", "3 passed", 0),
        ]
    ]

    messages = to_conversation_message_responses(lines)

    assert len(messages) == 1
    assert messages[0].tool_name == "command_execution"
    assert messages[0].tool_input == {
        "command": "pytest",
        "status": "completed",
        "exit_code": 0,
    }
    assert messages[0].tool_result == "3 passed"


def test_maps_the_valid_prompt_when_the_remaining_lines_are_invalid_or_unknown() -> (
    None
):
    lines = [
        "{",
        "[]",
        "{}",
        json.dumps({"type": "item.completed", "timestamp": TIMESTAMP}),
        json.dumps({"type": "unknown", "timestamp": TIMESTAMP}),
        json.dumps({"type": "dag.prompt", "timestamp": "bad", "text": "hidden"}),
        json.dumps(
            {
                "type": "dag.prompt",
                "timestamp": TIMESTAMP,
                "execution_id": "1",
                "text": "Fix CI",
            }
        ),
    ]

    messages = to_conversation_message_responses(lines)

    assert [(message.role, message.text) for message in messages] == [
        ("user", "Fix CI")
    ]
