"""A single message of a node's agent transcript."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field
from virgo_agentic_dag.api.web.api_requests.api_base_model import ApiBaseModel


class ConversationRoleEnum(StrEnum):
    """The author role of a transcript message."""

    USER = "user"
    ASSISTANT = "assistant"
    TOOL_USE = "tool_use"


class ConversationMessageResponse(ApiBaseModel):
    """A single message of a node's agent transcript."""

    uuid: str = Field(description="The id of the message in the transcript.")
    role: ConversationRoleEnum = Field(description="The author role of the message.")
    timestamp: datetime = Field(description="When the message is recorded.")
    is_sidechain: bool = Field(description="True where a subagent writes the message.")
    text: str = Field(
        default="", description="The text of a user or assistant message."
    )
    tool_name: str = Field(default="", description="The tool a tool_use message calls.")
    tool_input: dict[str, Any] = Field(
        default_factory=dict,
        description="The arguments of a tool_use message, keyed by parameter name.",
    )
    tool_result: str = Field(
        default="",
        description="The result of a tool_use message, empty where the tool sends none.",
    )
