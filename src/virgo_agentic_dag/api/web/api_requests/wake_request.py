"""The request body of a node wake."""

from __future__ import annotations

from pydantic import Field
from virgo_agentic_dag.api.web.api_requests.api_base_model import ApiBaseModel
from virgo_agentic_dag.domain.node.recovery_cause_enum import RecoveryCauseEnum


class WakeRequest(ApiBaseModel):
    """Represents a request to wake a node."""

    cause: RecoveryCauseEnum = Field(
        description="The cause recorded for the node's recovery."
    )
    action: str = Field(
        min_length=1, description="The action recorded for the node's recovery."
    )
    message: str = Field(
        min_length=1, description="The message that resumes the node's conversation."
    )
