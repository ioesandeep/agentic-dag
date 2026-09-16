"""NodeRepo held in a dict, for tests and rehearsals that want no database at all."""

from __future__ import annotations

from datetime import datetime

from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.node.node_state import NodeState


class InMemoryNodeRepo(NodeRepo):
    """Keeps node rows in process memory with the same contract as the real store."""

    def __init__(self) -> None:
        self._rows: dict[str, Node] = {}

    async def ensure_rows(self, graph_nodes: list[GraphNode], now: datetime) -> None:
        for graph_node in graph_nodes:
            if graph_node.id in self._rows:
                continue

            self._rows[graph_node.id] = Node(
                id=graph_node.id,
                title=graph_node.title,
                name=graph_node.name,
                state=NodeState.PENDING.value,
                created_at=now,
                updated_at=now,
                recovery_attempts_allowed=graph_node.recovery_attempts_allowed,
            )

    async def get_all(self) -> list[Node]:
        return list(self._rows.values())

    async def read(self, node_id: str) -> Node | None:
        return self._rows.get(node_id)

    async def get_nodes_by_state(self, state: NodeState) -> list[Node]:
        return [node for node in self._rows.values() if node.state == state.value]

    async def get_nodes_by_ids(self, node_ids: list[str]) -> list[Node]:
        return [self._rows[node_id] for node_id in node_ids if node_id in self._rows]

    async def update_state(self, node_id: str, state: NodeState, at: datetime) -> None:
        row = self._rows[node_id]
        self._rows[node_id] = Node(
            id=row.id,
            title=row.title,
            name=row.name,
            state=state.value,
            created_at=row.created_at,
            updated_at=at,
            recovery_attempts_allowed=row.recovery_attempts_allowed,
            pull_request_settled_at=row.pull_request_settled_at,
            learnings_extracted_at=row.learnings_extracted_at,
        )

    async def spend_recovery_attempt(self, node_id: str) -> None:
        row = self._rows[node_id]
        self._rows[node_id] = Node(
            id=row.id,
            title=row.title,
            name=row.name,
            state=row.state,
            created_at=row.created_at,
            updated_at=row.updated_at,
            recovery_attempts_allowed=row.recovery_attempts_allowed - 1,
            pull_request_settled_at=row.pull_request_settled_at,
            learnings_extracted_at=row.learnings_extracted_at,
        )

    async def record_pull_request_settled(self, node: Node, at: datetime) -> None:
        row = self._rows[node.id]
        self._rows[node.id] = Node(
            id=row.id,
            title=row.title,
            name=row.name,
            state=row.state,
            created_at=row.created_at,
            updated_at=row.updated_at,
            recovery_attempts_allowed=row.recovery_attempts_allowed,
            pull_request_settled_at=at,
            learnings_extracted_at=row.learnings_extracted_at,
        )

    async def get_nodes_due_for_learning_extraction(self) -> list[Node]:
        return [
            row for row in self._rows.values() if row.is_due_for_learning_extraction()
        ]

    async def record_learnings_extracted(self, nodes: list[Node], at: datetime) -> None:
        for node in nodes:
            row = self._rows[node.id]
            self._rows[node.id] = Node(
                id=row.id,
                title=row.title,
                name=row.name,
                state=row.state,
                created_at=row.created_at,
                updated_at=row.updated_at,
                recovery_attempts_allowed=row.recovery_attempts_allowed,
                pull_request_settled_at=row.pull_request_settled_at,
                learnings_extracted_at=at,
            )
