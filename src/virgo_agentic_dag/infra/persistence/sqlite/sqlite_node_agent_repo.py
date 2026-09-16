"""NodeAgentRepo on SQLite, one agent aggregate per node."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.repos.node_agent_repo import NodeAgentRepo
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase

_EAGER = (selectinload(NodeAgent.sessions), selectinload(NodeAgent.worktree))


class SqliteNodeAgentRepo(NodeAgentRepo):
    """Reads and writes an agent with its sessions and worktree in one aggregate."""

    def __init__(self, database: SqliteDatabase) -> None:
        self._database = database

    async def get_by_agent_id(self, agent_id: str) -> NodeAgent | None:
        async with self._database.open_session() as session:
            statement = (
                select(NodeAgent).options(*_EAGER).where(NodeAgent.id == agent_id)
            )

            return (await session.execute(statement)).scalar_one_or_none()

    async def get_by_node_id(self, node_id: str) -> NodeAgent | None:
        async with self._database.open_session() as session:
            statement = (
                select(NodeAgent).options(*_EAGER).where(NodeAgent.node_id == node_id)
            )

            return (await session.execute(statement)).scalar_one_or_none()

    async def save(self, agent: NodeAgent) -> None:
        async with self._database.open_session() as session:
            await session.merge(agent)
            await session.commit()
