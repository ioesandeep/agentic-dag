"""SlackNotificationRepo on SQLite, one row per node."""

from __future__ import annotations

from sqlalchemy import select
from virgo_agentic_dag.domain.persistence.entities.slack_notification import (
    SlackNotification,
)
from virgo_agentic_dag.domain.persistence.repos.slack_notification_repo import (
    SlackNotificationRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase


class SqliteSlackNotificationRepo(SlackNotificationRepo):
    """Reads and writes thread bindings through sessions the database hands out."""

    def __init__(self, database: SqliteDatabase) -> None:
        self._database = database

    async def get_by_node_id(self, node_id: str) -> SlackNotification | None:
        async with self._database.open_session() as session:
            statement = select(SlackNotification).where(
                SlackNotification.node_id == node_id
            )

            return (await session.execute(statement)).scalar_one_or_none()

    async def save(self, slack_notification: SlackNotification) -> None:
        async with self._database.open_session() as session:
            await session.merge(slack_notification)
            await session.commit()
