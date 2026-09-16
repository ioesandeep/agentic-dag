"""The interface for bringing a pull request that already exists under a run's management."""

from __future__ import annotations

from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.code.pull_request_details import (
    PullRequestDetails,
)


class NodeImporter(ABC):
    """Imports a pull request that already exists into a run as one of its nodes."""

    @abstractmethod
    async def import_node(
        self,
        graph_node: GraphNode,
        pr_details: PullRequestDetails,
        session_token: str | None = None,
    ) -> None:
        """Bring this node onto the pull request it takes over.

        Args:
            graph_node: the node that takes the pull request over.
            pr_details: the pull request's number, repository, and head branch.
            session_token: an agent session that already exists for the node to rest on
                and resume on its first wake. Without one the node's agent is launched
                now, under a session id that launch creates.
        """
