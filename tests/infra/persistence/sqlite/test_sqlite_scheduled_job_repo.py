import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_scheduled_job_repo import (
    SqliteScheduledJobRepo,
)

pytestmark = pytest.mark.integration

NOW = datetime(2026, 8, 2, tzinfo=UTC)


async def build_repo(tmp_path: Path) -> SqliteScheduledJobRepo:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite3'}")
    database = SqliteDatabase(engine)
    await database.upgrade_to_head()

    return SqliteScheduledJobRepo(database)


def build_job(interval_seconds: int = 300) -> ScheduledJob:
    return ScheduledJob(
        dag_name="demo",
        label=ScheduledJob.get_label("demo"),
        argv=json.dumps(["/venv/bin/dagctl", "start"]),
        interval_seconds=interval_seconds,
        working_directory="/runs/demo",
        log_path="/runs/demo/start.log",
        environment=json.dumps({"PATH": "/usr/bin"}),
        created_at=NOW,
    )


async def test_reads_back_the_job_when_one_was_saved(tmp_path: Path) -> None:
    repo = await build_repo(tmp_path)

    await repo.save(build_job())

    stored = await repo.get_by_dag_name("demo")
    assert stored is not None
    assert stored.label == "fyi.virgo.dag.demo"
    assert stored.get_argv() == ["/venv/bin/dagctl", "start"]
    assert stored.get_environment() == {"PATH": "/usr/bin"}


async def test_returns_nothing_when_the_dag_was_never_started(tmp_path: Path) -> None:
    repo = await build_repo(tmp_path)

    assert await repo.get_by_dag_name("demo") is None


async def test_keeps_one_row_when_the_same_dag_is_saved_again(tmp_path: Path) -> None:
    repo = await build_repo(tmp_path)
    await repo.save(build_job())

    await repo.save(build_job(interval_seconds=600))

    stored = await repo.get_by_dag_name("demo")
    assert stored is not None
    assert stored.interval_seconds == 600


async def test_forgets_the_job_when_it_is_deleted(tmp_path: Path) -> None:
    repo = await build_repo(tmp_path)
    job = build_job()
    await repo.save(job)

    await repo.delete(job)

    assert await repo.get_by_dag_name("demo") is None
