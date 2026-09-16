"""An event for an agent adopting an existing pull request."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.events.node_event import NodeEvent
from virgo_agentic_dag.domain.run.pr_details import PrDetails


@dataclass(frozen=True)
class PullRequestAdoptedEvent(NodeEvent):
    pr_details: PrDetails
