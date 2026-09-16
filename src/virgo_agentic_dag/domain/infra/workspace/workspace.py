"""The per-node git worktrees on this host's disk."""

from __future__ import annotations

from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree


class Workspace(ABC):
    """Provisions and reclaims the working copy one node builds in."""

    @abstractmethod
    async def provision(self, graph_node: GraphNode) -> WorkTree:
        """Return the record of this node's worktree, creating the worktree when it is missing."""

    @abstractmethod
    async def get_branch(self, worktree: WorkTree) -> str:
        """Return the branch the agent left checked out in this worktree."""

    @abstractmethod
    async def remove(self, worktree: WorkTree) -> None:
        """Delete this worktree from disk and mark its record reclaimed."""
