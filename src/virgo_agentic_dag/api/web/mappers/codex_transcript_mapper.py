"""Maps Codex execution events to conversation messages."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from virgo_agentic_dag.api.web.api_responses.conversation_message_response import (
    ConversationMessageResponse,
    ConversationRoleEnum,
)
from virgo_agentic_dag.domain.agent.transcript_line import TranscriptLine


def to_conversation_message_responses(
    transcript_lines: list[str],
) -> list[ConversationMessageResponse]:
    """Return the messages recorded by Codex executions."""
    messages: dict[str, ConversationMessageResponse] = {}
    for line in transcript_lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        is_record = isinstance(record, dict)
        if not is_record or "timestamp" not in record:
            continue

        try:
            message = _to_message(record)
        except (KeyError, TypeError, ValueError):
            continue

        if message is not None:
            messages[message.uuid] = message

    return list(messages.values())


def to_conversation_page_messages(
    page_lines: list[TranscriptLine], look_ahead_lines: list[TranscriptLine]
) -> list[ConversationMessageResponse]:
    """Return messages that start in the page lines, or an empty list when no message starts in those lines."""
    page_messages = _get_page_messages_by_uuid(page_lines)
    look_ahead_messages = _get_newest_messages_by_uuid(look_ahead_lines)

    newest_first: list[ConversationMessageResponse] = []
    for page_message in reversed(page_messages.values()):
        newest_message = look_ahead_messages.get(page_message.uuid, page_message)
        completed_message = newest_message.model_copy(update={"id": page_message.id})
        newest_first.append(completed_message)

    return newest_first


def _get_page_messages_by_uuid(
    page_lines: list[TranscriptLine],
) -> dict[str, ConversationMessageResponse]:
    """Return a dictionary from UUIDs to messages that start in the page lines, or an empty dictionary when no message starts in those lines."""
    page_messages: dict[str, ConversationMessageResponse] = {}
    for page_line in page_lines:
        record = _get_record(page_line.text)
        if record is None:
            continue

        message = _to_record_message(record)
        if message is None:
            continue

        earlier_message = page_messages.get(message.uuid)
        is_message_start = _is_message_start(record, message)
        if earlier_message is None and not is_message_start:
            continue

        message_id = f"{page_line.offset}:0"
        if earlier_message is not None:
            message_id = earlier_message.id

        page_messages[message.uuid] = message.model_copy(update={"id": message_id})

    return page_messages


def _get_newest_messages_by_uuid(
    transcript_lines: list[TranscriptLine],
) -> dict[str, ConversationMessageResponse]:
    """Return the newest message for each UUID in the transcript lines, or an empty dictionary when no transcript line converts to a message."""
    newest_messages: dict[str, ConversationMessageResponse] = {}
    for transcript_line in transcript_lines:
        record = _get_record(transcript_line.text)
        if record is None:
            continue

        message = _to_record_message(record)
        if message is not None:
            newest_messages[message.uuid] = message

    return newest_messages


def _get_record(line: str) -> dict[str, Any] | None:
    """Return a JSON object with a timestamp, or None when the line does not decode to such an object."""
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return None

    is_record = isinstance(record, dict)
    if not is_record or "timestamp" not in record:
        return None

    timestamped_record: dict[str, Any] = record

    return timestamped_record


def _to_record_message(record: dict[str, Any]) -> ConversationMessageResponse | None:
    """Return the record's conversation message, or None when conversion fails."""
    try:
        return _to_message(record)
    except (KeyError, TypeError, ValueError):
        return None


def _is_message_start(
    record: dict[str, Any], message: ConversationMessageResponse
) -> bool:
    """Return whether the record starts the message."""
    is_tool_message = message.role == ConversationRoleEnum.TOOL_USE

    return not is_tool_message or record["type"] == "item.started"


def _to_message(record: dict[str, Any]) -> ConversationMessageResponse | None:
    timestamp = datetime.fromisoformat(record["timestamp"])
    execution_id = record.get("execution_id", "")
    record_type = record.get("type")
    if record_type == "dag.prompt":
        return ConversationMessageResponse(
            uuid=f"{execution_id}:prompt",
            role=ConversationRoleEnum.USER,
            timestamp=timestamp,
            is_sidechain=False,
            text=record["text"],
        )

    if record_type not in ("item.started", "item.updated", "item.completed"):
        return None

    item = record["item"]
    message_id = f"{execution_id}:{item['id']}"

    return _to_item_message(item, message_id, timestamp)


def _to_item_message(
    item: dict[str, Any], message_id: str, timestamp: datetime
) -> ConversationMessageResponse | None:
    if item["type"] == "agent_message":
        return ConversationMessageResponse(
            uuid=message_id,
            role=ConversationRoleEnum.ASSISTANT,
            timestamp=timestamp,
            is_sidechain=False,
            text=item["text"],
        )

    if item["type"] in (
        "command_execution",
        "file_change",
        "mcp_tool_call",
        "web_search",
    ):
        return _to_tool_message(item, message_id, timestamp)

    return None


def _to_tool_message(
    item: dict[str, Any], message_id: str, timestamp: datetime
) -> ConversationMessageResponse:
    tool_name = item["type"]
    tool_result = item.get("aggregated_output", "")
    if tool_name == "mcp_tool_call":
        tool_name = f"{item['server']}.{item['tool']}"
        tool_result = json.dumps(item.get("result") or item.get("error"))

    tool_input = {
        key: value
        for key, value in item.items()
        if key not in ("id", "type", "aggregated_output", "result", "error")
    }

    return ConversationMessageResponse(
        uuid=message_id,
        role=ConversationRoleEnum.TOOL_USE,
        timestamp=timestamp,
        is_sidechain=False,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_result=tool_result,
    )
