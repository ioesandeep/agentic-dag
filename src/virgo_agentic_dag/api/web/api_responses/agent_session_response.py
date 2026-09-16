"""A single session of a node's agent."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field
from virgo_agentic_dag.api.web.api_requests.api_base_model import ApiBaseModel


class AgentSessionResponse(ApiBaseModel):
    """A single session of a node's agent."""

    id: int = Field(description="The id of the session.")
    started_at: datetime = Field(description="When the session starts.")
    ended_at: datetime | None = Field(
        default=None, description="When the session ends, null while it runs."
    )
    end_state: str = Field(
        description="The end state of the session, empty while it runs."
    )
    triggered_by: str = Field(description="The trigger of the session, launch or wake.")
