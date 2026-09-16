"""AgentSessionRepo on SQLite, one row per execution."""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.repos.agent_session_repo import (
    AgentSessionRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase


class SqliteAgentSessionRepo(AgentSessionRepo):
    """Writes execution rows through sessions the database hands out."""

    def __init__(self, database: SqliteDatabase) -> None:
        self._database = database

    async def add(self, session: AgentSession) -> None:
        async with self._database.open_session() as db_session:
            db_session.add(session)
            await db_session.commit()

    async def close(self, session: AgentSession) -> None:
        async with self._database.open_session() as db_session:
            statement = (
                update(AgentSession)
                .where(AgentSession.id == session.id)
                .values(
                    end_state=session.end_state,
                    ended_at=session.ended_at,
                    exit_code=session.exit_code,
                    log_tail=session.log_tail,
                )
            )
            await db_session.execute(statement)
            await db_session.commit()

    async def get_open_sessions(self) -> list[AgentSession]:
        async with self._database.open_session() as db_session:
            statement = (
                select(AgentSession)
                .options(selectinload(AgentSession.agent))
                .where(AgentSession.ended_at.is_(None))
            )
            result = await db_session.execute(statement)

            return list(result.scalars())
