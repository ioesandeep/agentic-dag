"""One node in the dag listing."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field
from virgo_agentic_dag.api.web.api_requests.api_base_model import ApiBaseModel


class NodePreviewResponse(ApiBaseModel):
    """One node of a dag, with its state and dependencies."""

    id: str = Field(description="The id of the node.")
    title: str = Field(description="The title of the node.")
    agent_name: str = Field(
        description="The display name of the agent assigned to this node."
    )
    state: str = Field(description="The state of this node.")
    depends_on: list[str] = Field(
        default_factory=list,
        description="The ids of the nodes this node depends on.",
    )
    updated_at: datetime | None = Field(
        default=None,
        description=(
            "The time of the last write to this node's state, null where there is none."
        ),
    )
