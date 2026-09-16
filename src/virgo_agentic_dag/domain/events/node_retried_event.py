"""An event for a human returning a node to the run."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.events.node_event import NodeEvent


@dataclass(frozen=True)
class NodeRetriedEvent(NodeEvent):
    pass
