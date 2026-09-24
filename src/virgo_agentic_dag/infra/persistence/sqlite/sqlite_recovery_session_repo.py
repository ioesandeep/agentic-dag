"""RecoverySessionRepo on SQLite, one row per execution of the recovery agent."""

from __future__ import annotations

from sqlalchemy import select, update
from virgo_agentic_dag.domain.persistence.entities.recovery_session import (
    RecoverySession,
)
from virgo_agentic_dag.domain.persistence.repos.recovery_session_repo import (
    RecoverySessionRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase


class SqliteRecoverySessionRepo(RecoverySessionRepo):
    """Writes recovery execution rows through sessions the database opens."""

    def __init__(self, database: SqliteDatabase) -> None:
        self._database = database

    async def add(self, recovery_session: RecoverySession) -> None:
        async with self._database.open_session() as db_session:
            db_session.add(recovery_session)
            await db_session.commit()

    async def close(self, recovery_session: RecoverySession) -> None:
        async with self._database.open_session() as db_session:
            statement = (
                update(RecoverySession)
                .where(RecoverySession.id == recovery_session.id)
                .values(ended_at=recovery_session.ended_at)
            )
            await db_session.execute(statement)
            await db_session.commit()

    async def find_open_session(self) -> RecoverySession | None:
        async with self._database.open_session() as db_session:
            statement = (
                select(RecoverySession)
                .where(RecoverySession.ended_at.is_(None))
                .order_by(RecoverySession.id.desc())
                .limit(1)
            )

            return (await db_session.execute(statement)).scalar_one_or_none()

    async def get_all(self) -> list[RecoverySession]:
        async with self._database.open_session() as db_session:
            statement = select(RecoverySession).order_by(RecoverySession.id.desc())

            return list((await db_session.execute(statement)).scalars())
