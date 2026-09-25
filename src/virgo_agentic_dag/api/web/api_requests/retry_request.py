"""The request body of a node retry."""

from __future__ import annotations

from pydantic import Field
from virgo_agentic_dag.api.web.api_requests.api_base_model import ApiBaseModel


class RetryRequest(ApiBaseModel):
    """Represents the request options for retrying a node."""

    reset: bool = Field(
        default=False,
        description=(
            "Whether the retry starts a new conversation instead of resuming the "
            "recorded one, false when omitted."
        ),
    )
