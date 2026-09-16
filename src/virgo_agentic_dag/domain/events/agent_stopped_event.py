"""An event for a node that an agent cannot advance alone."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.events.node_event import NodeEvent
from virgo_agentic_dag.domain.run.pr_details import PrDetails


@dataclass(frozen=True)
class AgentStoppedEvent(NodeEvent):
    # Why the node's agent stopped.
    reason: str
    # The pull request the node stopped on.
    pr_details: PrDetails | None = None
    # The trailing lines of the stopped session's log.
    log_tail: str = ""
