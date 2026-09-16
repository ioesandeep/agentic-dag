"""An event for a dag with all nodes in terminal states."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta

from virgo_agentic_dag.domain.events.dag_event import DagEvent
from virgo_agentic_dag.domain.node.node_state import NodeState


@dataclass(frozen=True)
class DagCompletedEvent(DagEvent):
    node_counts_by_state: Mapping[NodeState, int]
    # The duration from the earliest node creation time to dag completion.
    elapsed_time: timedelta
