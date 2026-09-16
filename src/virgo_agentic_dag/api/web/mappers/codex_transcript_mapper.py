"""Maps Codex execution events to conversation messages."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from virgo_agentic_dag.api.web.api_responses.conversation_message_response import (
    ConversationMessageResponse,
    ConversationRoleEnum,
)


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
