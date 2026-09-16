"""An event for opening a pull request for a node."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.events.node_event import NodeEvent
from virgo_agentic_dag.domain.run.pr_details import PrDetails


@dataclass(frozen=True)
class PullRequestOpenedEvent(NodeEvent):
    pr_details: PrDetails
