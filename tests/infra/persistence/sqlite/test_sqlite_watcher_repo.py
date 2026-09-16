from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from virgo_agentic_dag.domain.persistence.entities.watcher import Watcher
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_watcher_repo import (
    SqliteWatcherRepo,
)

pytestmark = pytest.mark.integration

NOW = datetime(2026, 8, 2, tzinfo=UTC)


async def build_repo(tmp_path: Path) -> SqliteWatcherRepo:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite3'}")
    database = SqliteDatabase(engine)
    await database.upgrade_to_head()

    return SqliteWatcherRepo(database)


def build_watcher(pid: int = 4242) -> Watcher:
    return Watcher(dag_name="demo", pid=pid, started_at=NOW)


async def test_reads_back_the_watcher_when_one_was_saved(tmp_path: Path) -> None:
    repo = await build_repo(tmp_path)

    await repo.save(build_watcher())

    found = await repo.get_by_dag_name("demo")
    assert found is not None and found.pid == 4242


async def test_keeps_one_row_when_the_same_dag_is_saved_again(tmp_path: Path) -> None:
    repo = await build_repo(tmp_path)
    await repo.save(build_watcher(pid=1))

    await repo.save(build_watcher(pid=2))

    found = await repo.get_by_dag_name("demo")
    assert found is not None and found.pid == 2


async def test_returns_none_after_the_watcher_is_deleted(tmp_path: Path) -> None:
    repo = await build_repo(tmp_path)
    await repo.save(build_watcher())

    await repo.delete(build_watcher())

    assert await repo.get_by_dag_name("demo") is None
