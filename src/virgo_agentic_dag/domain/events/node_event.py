"""The event describing one state change on a node."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from virgo_agentic_dag.domain.events.event import Event
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType


@dataclass(frozen=True)
class NodeEvent(Event):
    node_id: str
    # the lifecycle moment this event marks
    type: NotificationType
    created_at: datetime
    updated_at: datetime
    # what the node is for
    title: str
    agent_name: str
