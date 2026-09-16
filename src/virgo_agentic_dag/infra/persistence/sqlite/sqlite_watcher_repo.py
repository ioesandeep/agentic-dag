"""Stores each run's watcher row in its SQLite database."""

from __future__ import annotations

from sqlalchemy import delete, select
from virgo_agentic_dag.domain.persistence.entities.watcher import Watcher
from virgo_agentic_dag.domain.persistence.repos.watcher_repo import WatcherRepo
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase


class SqliteWatcherRepo(WatcherRepo):
    """Writes watcher rows through sessions the database hands out."""

    def __init__(self, database: SqliteDatabase) -> None:
        self._database = database

    async def save(self, watcher: Watcher) -> None:
        async with self._database.open_session() as session:
            await session.merge(watcher)
            await session.commit()

    async def get_by_dag_name(self, dag_name: str) -> Watcher | None:
        async with self._database.open_session() as session:
            statement = select(Watcher).where(Watcher.dag_name == dag_name)
            result = await session.execute(statement)

            return result.scalars().first()

    async def delete(self, watcher: Watcher) -> None:
        async with self._database.open_session() as session:
            statement = delete(Watcher).where(Watcher.dag_name == watcher.dag_name)
            await session.execute(statement)
            await session.commit()
