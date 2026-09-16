"""The controller's own state for a node, independent of its pull request."""

from __future__ import annotations

from enum import Enum


class NodeState(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESTING = "resting"
    NEEDS_HUMAN = "needs_human"
    MERGED = "merged"
    ERRORED = "errored"
    SKIPPED = "skipped"

    def is_terminal(self) -> bool:
        """Report whether the controller is finished with this node for good."""
        return self in (
            NodeState.MERGED,
            NodeState.NEEDS_HUMAN,
            NodeState.ERRORED,
            NodeState.SKIPPED,
        )
