"""Where each node's controller-side row lives, whatever database holds it."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.node.node_state import NodeState


class NodeRepo(ABC):
    """Reads and writes one run's nodes, and keeps them in step with the graph."""

    @abstractmethod
    async def ensure_rows(self, graph_nodes: list[GraphNode], now: datetime) -> None:
        """Create a pending node for every one the graph declares and the store lacks."""

    @abstractmethod
    async def get_all(self) -> list[Node]:
        """Return every node of this run."""

    @abstractmethod
    async def read(self, node_id: str) -> Node | None:
        """Return this node, or None if the graph never opened it."""

    @abstractmethod
    async def get_nodes_by_state(self, state: NodeState) -> list[Node]:
        """Return every node currently in this state."""

    @abstractmethod
    async def get_nodes_by_ids(self, node_ids: list[str]) -> list[Node]:
        """Return the nodes with these ids, in the order the store finds them."""

    @abstractmethod
    async def update_state(self, node_id: str, state: NodeState, at: datetime) -> None:
        """Move this node to the given state, stamping when it happened."""

    @abstractmethod
    async def spend_recovery_attempt(self, node_id: str) -> None:
        """Take a single recovery attempt off this node's allowance."""

    @abstractmethod
    async def record_pull_request_settled(self, node: Node, at: datetime) -> None:
        """Record when this node's pull request settled."""

    @abstractmethod
    async def get_nodes_due_for_learning_extraction(self) -> list[Node]:
        """Return every node due for learning extraction."""

    @abstractmethod
    async def record_learnings_extracted(self, nodes: list[Node], at: datetime) -> None:
        """Record when the learnings of these nodes were extracted."""
