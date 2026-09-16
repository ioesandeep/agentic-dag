"""ScheduledJobRepo on SQLite, one row per dag."""

from __future__ import annotations

from sqlalchemy import delete, select
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.domain.persistence.repos.scheduled_job_repo import (
    ScheduledJobRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase


class SqliteScheduledJobRepo(ScheduledJobRepo):
    """Writes scheduled job rows through sessions the database hands out."""

    def __init__(self, database: SqliteDatabase) -> None:
        self._database = database

    async def save(self, scheduled_job: ScheduledJob) -> None:
        async with self._database.open_session() as session:
            await session.merge(scheduled_job)
            await session.commit()

    async def get_by_dag_name(self, dag_name: str) -> ScheduledJob | None:
        async with self._database.open_session() as session:
            statement = select(ScheduledJob).where(ScheduledJob.dag_name == dag_name)
            result = await session.execute(statement)

            return result.scalars().first()

    async def delete(self, scheduled_job: ScheduledJob) -> None:
        async with self._database.open_session() as session:
            statement = delete(ScheduledJob).where(
                ScheduledJob.dag_name == scheduled_job.dag_name
            )
            await session.execute(statement)
            await session.commit()
