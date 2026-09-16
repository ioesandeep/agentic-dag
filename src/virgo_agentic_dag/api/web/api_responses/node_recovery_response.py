"""A single recorded failure of a node and the recovery decision for it."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field
from virgo_agentic_dag.api.web.api_requests.api_base_model import ApiBaseModel


class NodeRecoveryResponse(ApiBaseModel):
    """A single recorded failure of a node and the recovery decision for it."""

    id: int = Field(description="The node recovery identifier.")
    session_id: int = Field(description="The id of the agent session that ended.")
    detected_at: datetime = Field(description="When the failure is detected.")
    cause: str = Field(description="The cause of the failure.")
    recoverable: bool = Field(description="Whether the node can be recovered.")
    recover_at: datetime = Field(
        description="When the node becomes eligible for recovery."
    )
    action: str = Field(description="The recovery action for the node failure.")
