"""An event for a dag starting on its first host invocation."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.events.dag_event import DagEvent


@dataclass(frozen=True)
class DagStartedEvent(DagEvent):
    node_count: int
    in_progress_node_count: int
