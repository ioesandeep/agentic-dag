from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_agent_session_repo import (
    SqliteAgentSessionRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase

pytestmark = pytest.mark.integration


@pytest.fixture
async def database(tmp_path: Path) -> AsyncGenerator[SqliteDatabase]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite3'}")
    database = SqliteDatabase(engine)
    await database.upgrade_to_head()

    yield database

    await database.dispose()


@pytest.fixture
def started_at() -> datetime:
    return datetime(2026, 9, 3, tzinfo=UTC)


async def test_close_records_the_exit_code_and_log_tail_on_the_session_row(
    database: SqliteDatabase, started_at: datetime
) -> None:
    repo = SqliteAgentSessionRepo(database)
    open_session = AgentSession(
        agent_id="agent-1", started_at=started_at, triggered_by="launch"
    )
    await repo.add(open_session)
    closed_session = AgentSession(
        id=open_session.id,
        agent_id="agent-1",
        started_at=started_at,
        ended_at=started_at,
        end_state="finished",
        exit_code=1,
        log_tail="Error: Reached max turns (120)",
    )

    await repo.close(closed_session)

    async with database.open_session() as db_session:
        row = await db_session.get(AgentSession, open_session.id)

    assert row is not None
    assert (row.exit_code, row.log_tail) == (1, "Error: Reached max turns (120)")
