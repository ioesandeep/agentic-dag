from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from virgo_agentic_dag.domain.persistence.entities.slack_notification import (
    SlackNotification,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_slack_notification_repo import (
    SqliteSlackNotificationRepo,
)

pytestmark = pytest.mark.integration

NOW = datetime(2026, 7, 31, tzinfo=UTC)


async def build_repo(tmp_path: Path) -> SqliteSlackNotificationRepo:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite3'}")
    database = SqliteDatabase(engine)
    await database.upgrade_to_head()

    return SqliteSlackNotificationRepo(database)


async def test_reads_back_the_thread_when_a_binding_was_saved(tmp_path: Path) -> None:
    repo = await build_repo(tmp_path)
    binding = SlackNotification(
        node_id="A", channel="#dag", thread_id="1700.1", created_at=NOW
    )

    await repo.save(binding)

    stored = await repo.get_by_node_id("A")
    assert stored is not None
    assert (stored.channel, stored.thread_id) == ("#dag", "1700.1")


async def test_returns_nothing_when_the_node_has_never_spoken(tmp_path: Path) -> None:
    repo = await build_repo(tmp_path)

    assert await repo.get_by_node_id("A") is None
