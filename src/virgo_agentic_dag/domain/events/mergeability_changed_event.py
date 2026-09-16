"""An event for a change to a pull request's mergeability."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.events.node_event import NodeEvent
from virgo_agentic_dag.domain.run.pr_details import PrDetails


@dataclass(frozen=True)
class MergeabilityChangedEvent(NodeEvent):
    pr_details: PrDetails
