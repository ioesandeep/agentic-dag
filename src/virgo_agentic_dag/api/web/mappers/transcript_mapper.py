"""Converts transcript lines to conversation message responses."""

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
    """Convert the lines of a session file to the messages they record."""
    records = _list_json_records(transcript_lines)
    message_records = [
        record
        for record in records
        if record["type"] in (ConversationRoleEnum.USER, ConversationRoleEnum.ASSISTANT)
    ]
    tool_results = _find_tool_results(message_records)

    conversation_messages: list[ConversationMessageResponse] = []
    for message_record in message_records:
        record_messages = _to_conversation_messages(message_record, tool_results)
        conversation_messages.extend(record_messages)

    return conversation_messages


def to_conversation_page_messages(
    page_lines: list[TranscriptLine], look_ahead_lines: list[TranscriptLine]
) -> list[ConversationMessageResponse]:
    """Return conversation messages for the page lines, or an empty list when no page line decodes to a message record."""
    page_records = _get_message_records_by_offset(page_lines)
    look_ahead_texts = [look_ahead_line.text for look_ahead_line in look_ahead_lines]
    look_ahead_records = _list_json_records(look_ahead_texts)
    look_ahead_message_records = [
        record for record in look_ahead_records if _is_message_record(record)
    ]
    tool_results = _find_tool_results(
        [*page_records.values(), *look_ahead_message_records]
    )

    page_messages: list[ConversationMessageResponse] = []
    for record_offset, message_record in page_records.items():
        record_messages = _to_conversation_messages(message_record, tool_results)
        for message_index, record_message in enumerate(record_messages):
            message_id = f"{record_offset}:{message_index}"
            page_message = record_message.model_copy(update={"id": message_id})
            page_messages.append(page_message)

    page_messages.reverse()

    return page_messages


def _get_message_records_by_offset(
    page_lines: list[TranscriptLine],
) -> dict[int, dict[str, Any]]:
    """Return message records by line offset, or an empty dictionary when no page line decodes to a message record."""
    message_records: dict[int, dict[str, Any]] = {}
    for page_line in page_lines:
        try:
            record = json.loads(page_line.text)
        except json.JSONDecodeError:
            continue

        is_message = _is_message_record(record)
        if is_message:
            message_records[page_line.offset] = record

    return message_records


def _is_message_record(record: dict[str, Any]) -> bool:
    """Return whether the record is a user or assistant message."""
    return record["type"] in (ConversationRoleEnum.USER, ConversationRoleEnum.ASSISTANT)


def _list_json_records(transcript_lines: list[str]) -> list[dict[str, Any]]:
    """Return the json records of these lines, without the lines that do not parse."""
    records: list[dict[str, Any]] = []
    for line in transcript_lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        records.append(record)

    return records


def _find_tool_results(message_records: list[dict[str, Any]]) -> dict[str, str]:
    """Returns tool result text by tool use ID."""
    tool_results: dict[str, str] = {}
    for message_record in message_records:
        for block in _get_content_blocks(message_record):
            if block["type"] == "tool_result":
                tool_results[block["tool_use_id"]] = _get_result_text(block["content"])

    return tool_results


def _get_content_blocks(message_record: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the content blocks of a message record."""
    content = message_record["message"]["content"]
    if isinstance(content, str):
        return [{"type": "text", "text": content}]

    blocks: list[dict[str, Any]] = content

    return blocks


def _get_result_text(content: str | list[dict[str, Any]]) -> str:
    """Return the text of a tool result, without its images."""
    if isinstance(content, str):
        return content

    texts = [block["text"] for block in content if block["type"] == "text"]

    return "\n".join(texts)


def _to_conversation_messages(
    message_record: dict[str, Any], tool_results: dict[str, str]
) -> list[ConversationMessageResponse]:
    """Convert a single message record to its messages."""
    conversation_messages: list[ConversationMessageResponse] = []
    for block in _get_content_blocks(message_record):
        if block["type"] == "text":
            text_message = _to_text_message(message_record, block)
            conversation_messages.append(text_message)

        if block["type"] == "tool_use":
            tool_use_message = _to_tool_use_message(message_record, block, tool_results)
            conversation_messages.append(tool_use_message)

    return conversation_messages


def _to_text_message(
    message_record: dict[str, Any], block: dict[str, Any]
) -> ConversationMessageResponse:
    """Convert a text block to a user or assistant message."""
    return ConversationMessageResponse(
        uuid=message_record["uuid"],
        role=ConversationRoleEnum(message_record["type"]),
        timestamp=datetime.fromisoformat(message_record["timestamp"]),
        is_sidechain=message_record["isSidechain"],
        text=block["text"],
    )


def _to_tool_use_message(
    message_record: dict[str, Any], block: dict[str, Any], tool_results: dict[str, str]
) -> ConversationMessageResponse:
    """Convert a tool_use block to a tool_use message with its result."""
    return ConversationMessageResponse(
        uuid=message_record["uuid"],
        role=ConversationRoleEnum.TOOL_USE,
        timestamp=datetime.fromisoformat(message_record["timestamp"]),
        is_sidechain=message_record["isSidechain"],
        tool_name=block["name"],
        tool_input=block["input"],
        tool_result=tool_results.get(block["id"], ""),
    )
