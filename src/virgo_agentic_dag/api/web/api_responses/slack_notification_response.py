"""A single Slack notification thread opened for a node."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field
from virgo_agentic_dag.api.web.api_requests.api_base_model import ApiBaseModel


class SlackNotificationResponse(ApiBaseModel):
    """A single Slack notification thread opened for a node."""

    id: int = Field(description="The id of the notification.")
    channel: str = Field(description="The Slack channel the notification is sent to.")
    thread_id: str = Field(
        description="The id of the Slack thread the notification opens."
    )
    created_at: datetime = Field(description="When the notification is sent.")
