"""One line of a dag's audit trail."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field
from virgo_agentic_dag.api.web.api_requests.api_base_model import ApiBaseModel


class AuditLineResponse(ApiBaseModel):
    """One transition of a dag, with the note that explains it."""

    created_at: datetime = Field(description="When the transition is recorded.")
    node_id: str = Field(description="The id of the node the transition belongs to.")
    state: str = Field(description="The state the node moves to.")
    note: str = Field(description="The note that explains the transition.")
