"""An event for a human removing a node from the run."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.events.node_event import NodeEvent


@dataclass(frozen=True)
class NodeSkippedEvent(NodeEvent):
    pass
