"""NodeRepo on SQLite, one row per node of the run."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase

_EAGER = (
    selectinload(Node.agent).selectinload(NodeAgent.sessions),
    selectinload(Node.agent).selectinload(NodeAgent.worktree),
)


class SqliteNodeRepo(NodeRepo):
    """Reads and writes node rows through sessions the database hands out."""

    def __init__(self, database: SqliteDatabase) -> None:
        self._database = database

    async def ensure_rows(self, graph_nodes: list[GraphNode], now: datetime) -> None:
        async with self._database.open_session() as session:
            existing = set((await session.execute(select(Node.id))).scalars())
            for graph_node in graph_nodes:
                if graph_node.id in existing:
                    continue

                node = Node(
                    id=graph_node.id,
                    title=graph_node.title,
                    name=graph_node.name,
                    state=NodeState.PENDING.value,
                    created_at=now,
                    updated_at=now,
                    recovery_attempts_allowed=graph_node.recovery_attempts_allowed,
                )
                session.add(node)

            await session.commit()

    async def get_all(self) -> list[Node]:
        async with self._database.open_session() as session:
            statement = select(Node).options(*_EAGER)

            return list((await session.execute(statement)).scalars())

    async def read(self, node_id: str) -> Node | None:
        async with self._database.open_session() as session:
            statement = select(Node).options(*_EAGER).where(Node.id == node_id)

            return (await session.execute(statement)).scalar_one_or_none()

    async def get_nodes_by_state(self, state: NodeState) -> list[Node]:
        async with self._database.open_session() as session:
            statement = select(Node).options(*_EAGER).where(Node.state == state.value)

            return list((await session.execute(statement)).scalars())

    async def get_nodes_by_ids(self, node_ids: list[str]) -> list[Node]:
        async with self._database.open_session() as session:
            statement = select(Node).options(*_EAGER).where(Node.id.in_(node_ids))

            return list((await session.execute(statement)).scalars())

    async def update_state(self, node_id: str, state: NodeState, at: datetime) -> None:
        async with self._database.open_session() as session:
            statement = (
                update(Node)
                .where(Node.id == node_id)
                .values(state=state.value, updated_at=at)
            )
            await session.execute(statement)
            await session.commit()

    async def spend_recovery_attempt(self, node_id: str) -> None:
        async with self._database.open_session() as session:
            statement = (
                update(Node)
                .where(Node.id == node_id)
                .values(recovery_attempts_allowed=Node.recovery_attempts_allowed - 1)
            )
            await session.execute(statement)
            await session.commit()

    async def record_pull_request_settled(self, node: Node, at: datetime) -> None:
        async with self._database.open_session() as session:
            statement = (
                update(Node)
                .where(Node.id == node.id)
                .values(pull_request_settled_at=at)
            )
            await session.execute(statement)
            await session.commit()

    async def get_nodes_due_for_learning_extraction(self) -> list[Node]:
        async with self._database.open_session() as session:
            statement = (
                select(Node)
                .options(*_EAGER)
                .where(
                    Node.pull_request_settled_at.is_not(None),
                    Node.learnings_extracted_at.is_(None),
                )
            )

            return list((await session.execute(statement)).scalars())

    async def record_learnings_extracted(self, nodes: list[Node], at: datetime) -> None:
        node_ids = [node.id for node in nodes]
        async with self._database.open_session() as session:
            statement = (
                update(Node)
                .where(Node.id.in_(node_ids))
                .values(learnings_extracted_at=at)
            )
            await session.execute(statement)
            await session.commit()
