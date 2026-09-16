"""AuditEntryRepo on SQLite, append-only by construction."""

from __future__ import annotations

from sqlalchemy import select
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase


class SqliteAuditEntryRepo(AuditEntryRepo):
    """Writes each transition as a new row and reads the history back in id order."""

    def __init__(self, database: SqliteDatabase) -> None:
        self._database = database

    async def save(self, audit_entry: AuditEntry) -> None:
        async with self._database.open_session() as session:
            session.add(audit_entry)
            await session.commit()

    async def get_all(self) -> list[AuditEntry]:
        async with self._database.open_session() as session:
            statement = select(AuditEntry).order_by(AuditEntry.id)

            return list((await session.execute(statement)).scalars())
