"""One dag in the dag listing."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field
from virgo_agentic_dag.api.web.api_requests.api_base_model import ApiBaseModel
from virgo_agentic_dag.api.web.api_responses.node_preview_response import (
    NodePreviewResponse,
)


class DagSummaryResponse(ApiBaseModel):
    """One dag on this host."""

    name: str = Field(description="The name of the dag.")
    base_branch: str = Field(
        description="The branch this dag's pull requests merge into."
    )
    tick_interval_seconds: int = Field(
        description="The seconds the host waits between control passes."
    )
    node_count: int = Field(default=0, description="The number of nodes in this dag.")
    nodes: list[NodePreviewResponse] = Field(
        default_factory=list,
        description="The nodes of this dag.",
    )
    last_activity_at: datetime | None = Field(
        default=None,
        description=(
            "The last node state write time in this dag, null where there is none."
        ),
    )
    is_scheduled: bool = Field(
        default=False,
        description="True where a host job is registered to advance this dag.",
    )
    is_watching: bool = Field(
        default=False,
        description="True where a watcher process is recorded for this dag.",
    )
    is_readable: bool = Field(
        default=True, description="False where this dag's database does not open."
    )
