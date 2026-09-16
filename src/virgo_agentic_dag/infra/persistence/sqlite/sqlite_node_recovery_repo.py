"""NodeRecoveryRepo on SQLite, one row per failure of a node."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from virgo_agentic_dag.domain.persistence.entities.node_recovery import NodeRecovery
from virgo_agentic_dag.domain.persistence.repos.node_recovery_repo import (
    NodeRecoveryRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase


class SqliteNodeRecoveryRepo(NodeRecoveryRepo):
    """Writes and queries failure rows through sessions the database opens."""

    def __init__(self, database: SqliteDatabase) -> None:
        self._database = database

    async def add(self, node_recovery: NodeRecovery) -> None:
        async with self._database.open_session() as session:
            session.add(node_recovery)
            await session.commit()

    async def get_newest_recovery_by_node_id(self, node_id: str) -> NodeRecovery | None:
        async with self._database.open_session() as session:
            statement = (
                select(NodeRecovery)
                .where(NodeRecovery.node_id == node_id)
                .order_by(NodeRecovery.id.desc())
                .limit(1)
            )

            return (await session.execute(statement)).scalar_one_or_none()

    async def get_due_recoveries(self, recover_at: datetime) -> list[NodeRecovery]:
        async with self._database.open_session() as session:
            newest_ids = select(func.max(NodeRecovery.id)).group_by(
                NodeRecovery.node_id
            )
            statement = (
                select(NodeRecovery)
                .where(
                    NodeRecovery.id.in_(newest_ids),
                    NodeRecovery.recoverable.is_(True),
                    NodeRecovery.recover_at <= recover_at,
                )
                .order_by(NodeRecovery.id)
            )
            result = await session.execute(statement)

            return list(result.scalars())

    async def count_by_node_id(self, node_id: str) -> int:
        async with self._database.open_session() as session:
            statement = (
                select(func.count())
                .select_from(NodeRecovery)
                .where(NodeRecovery.node_id == node_id)
            )
            count: int = (await session.execute(statement)).scalar_one()

            return count
