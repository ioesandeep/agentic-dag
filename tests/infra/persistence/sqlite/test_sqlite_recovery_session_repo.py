from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from virgo_agentic_dag.domain.persistence.entities.recovery_session import (
    RecoverySession,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_recovery_session_repo import (
    SqliteRecoverySessionRepo,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def started_at() -> datetime:
    return datetime(2026, 9, 5, tzinfo=UTC)


@pytest.fixture
async def repo(tmp_path: Path) -> AsyncGenerator[SqliteRecoverySessionRepo]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite3'}")
    database = SqliteDatabase(engine)
    await database.upgrade_to_head()

    yield SqliteRecoverySessionRepo(database)

    await database.dispose()


async def test_find_open_session_returns_the_row_when_it_has_not_ended(
    repo: SqliteRecoverySessionRepo, started_at: datetime
) -> None:
    recovery_session = RecoverySession(
        session_token="token-1", pid=4242, started_at=started_at, node_ids='["A", "B"]'
    )
    await repo.add(recovery_session)

    open_recovery_session = await repo.find_open_session()

    assert open_recovery_session is not None
    assert (open_recovery_session.pid, open_recovery_session.get_node_ids()) == (
        4242,
        ["A", "B"],
    )


async def test_find_open_session_returns_none_when_the_row_is_closed(
    repo: SqliteRecoverySessionRepo, started_at: datetime
) -> None:
    recovery_session = RecoverySession(
        session_token="token-1", pid=4242, started_at=started_at, node_ids='["A"]'
    )
    await repo.add(recovery_session)
    closed_recovery_session = RecoverySession(
        id=recovery_session.id,
        session_token="token-1",
        pid=4242,
        started_at=started_at,
        ended_at=started_at,
        node_ids='["A"]',
    )

    await repo.close(closed_recovery_session)

    assert await repo.find_open_session() is None
