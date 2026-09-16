"""The worktree of a node's agent."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field
from virgo_agentic_dag.api.web.api_requests.api_base_model import ApiBaseModel


class WorktreeResponse(ApiBaseModel):
    """The worktree of a node's agent."""

    name: str = Field(description="The name of the worktree.")
    absolute_path: str = Field(
        description="The absolute path of the worktree on this host."
    )
    branch: str = Field(
        description="The branch of the worktree, empty where none is published."
    )
    pr_number: int = Field(
        description=(
            "The number of the pull request opened from the worktree, "
            "0 where there is none."
        )
    )
    created_at: datetime = Field(description="When the worktree is created.")
    reclaimed_at: datetime | None = Field(
        default=None,
        description=(
            "When the disk copy of the worktree is removed, null while it is on disk."
        ),
    )
    signal_marks: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "The mark of the last detected change of each pull request signal, "
            "keyed by signal name."
        ),
    )
