"""One SQLite engine and its session factory, so no repository holds either itself."""

from __future__ import annotations

from importlib.resources import files

import virgo_agentic_dag
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.node_recovery import NodeRecovery
from virgo_agentic_dag.domain.persistence.entities.recovery_session import (
    RecoverySession,
)
from virgo_agentic_dag.domain.persistence.entities.slack_notification import (
    SlackNotification,
)
from virgo_agentic_dag.domain.persistence.entities.watcher import Watcher
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree

MAPPED_ENTITIES = (
    Node,
    NodeAgent,
    AgentSession,
    WorkTree,
    AuditEntry,
    SlackNotification,
    ScheduledJob,
    Watcher,
    NodeRecovery,
    RecoverySession,
)


class SqliteDatabase:
    """Owns the connection to one SQLite database and hands out sessions against it."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self._session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def upgrade_to_head(self) -> None:
        """Apply every migration the database has not recorded yet."""
        async with self._engine.begin() as connection:
            await connection.run_sync(self._upgrade_to_head)

    @staticmethod
    def _upgrade_to_head(connection: Connection) -> None:
        migrations_path = files(virgo_agentic_dag) / "migrations"
        config = Config()
        config.set_main_option("script_location", str(migrations_path))
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

    def open_session(self) -> AsyncSession:
        """Return a session scoped to one unit of work, entered as a context manager."""
        return self._session_factory()

    async def dispose(self) -> None:
        """Close every pooled connection and release the engine."""
        await self._engine.dispose()
