"""A single execution of the recovery agent over a batch of nodes."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field
from virgo_agentic_dag.api.web.api_requests.api_base_model import ApiBaseModel


class RecoverySessionResponse(ApiBaseModel):
    """A single execution of the recovery agent over a batch of nodes."""

    id: int = Field(description="The recovery session id.")
    started_at: datetime = Field(description="The recovery session start time.")
    ended_at: datetime | None = Field(
        default=None,
        description="The recovery session end time, or null when no end time is recorded.",
    )
    node_ids: list[str] = Field(
        description="The ids of the nodes in the recovery session."
    )
    is_process_alive: bool = Field(
        description="Whether the recovery session process is alive."
    )
