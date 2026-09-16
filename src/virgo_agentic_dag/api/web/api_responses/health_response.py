"""The liveness status of this server."""

from __future__ import annotations

from pydantic import Field
from virgo_agentic_dag.api.web.api_requests.api_base_model import ApiBaseModel


class HealthResponse(ApiBaseModel):
    """The liveness status of this server."""

    status: str = Field(description="The value ok while this server is up.")
