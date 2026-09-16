"""An event for an agent resuming work on a node."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.events.node_event import NodeEvent


@dataclass(frozen=True)
class WorkResumedEvent(NodeEvent):
    pass
