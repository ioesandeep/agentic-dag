"""A response model for a page of a node's agent transcript."""

from __future__ import annotations

from pydantic import Field
from virgo_agentic_dag.api.web.api_requests.api_base_model import ApiBaseModel
from virgo_agentic_dag.api.web.api_responses.conversation_message_response import (
    ConversationMessageResponse,
)
from virgo_agentic_dag.api.web.api_responses.pagination_response import (
    PaginationResponse,
)


class ConversationPageResponse(ApiBaseModel):
    """A page of a node's agent transcript."""

    session_id: str = Field(
        description="The agent resume token, or an empty string when the node has no transcript."
    )
    messages: list[ConversationMessageResponse] = Field(
        description="The messages in newest-first order, or an empty list when the page has no messages."
    )
    pagination: PaginationResponse = Field(
        description="The pagination for pages of older messages."
    )
