"""An event for a turn that ends with a commit push."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.events.node_event import NodeEvent
from virgo_agentic_dag.domain.run.pr_details import PrDetails


@dataclass(frozen=True)
class CommitPushedEvent(NodeEvent):
    pr_details: PrDetails
    # The number of commits the session pushes to the pull request.
    commit_count: int
