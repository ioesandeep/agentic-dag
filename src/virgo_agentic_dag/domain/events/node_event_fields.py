"""The fields defined for every node event."""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from virgo_agentic_dag.domain.notifications.notification_type import NotificationType


class NodeEventFields(TypedDict):
    node_id: str
    type: NotificationType
    created_at: datetime
    updated_at: datetime
    title: str
    agent_name: str
