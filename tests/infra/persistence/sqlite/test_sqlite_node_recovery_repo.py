from collections.abc import AsyncGenerator, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from virgo_agentic_dag.domain.node.recovery_cause_enum import RecoveryCauseEnum
from virgo_agentic_dag.domain.persistence.entities.node_recovery import NodeRecovery
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_recovery_repo import (
    SqliteNodeRecoveryRepo,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 9, 3, tzinfo=UTC)


@pytest.fixture
def later(now: datetime) -> datetime:
    return now + timedelta(hours=1)


@pytest.fixture
async def repo(tmp_path: Path) -> AsyncGenerator[SqliteNodeRecoveryRepo]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite3'}")
    database = SqliteDatabase(engine)
    await database.upgrade_to_head()

    yield SqliteNodeRecoveryRepo(database)

    await database.dispose()


@pytest.fixture
def build_failure() -> Callable[[str, datetime, bool], NodeRecovery]:
    return lambda node_id, at, recoverable: NodeRecovery(
        node_id=node_id,
        session_id=1,
        detected_at=at,
        cause=RecoveryCauseEnum.PROVIDER_FAILURE.value,
        recoverable=recoverable,
        recover_at=at,
        action="",
    )


async def test_get_newest_recovery_by_node_id_returns_the_last_added_row_when_several_rows_exist(
    repo: SqliteNodeRecoveryRepo,
    now: datetime,
    later: datetime,
    build_failure: Callable[[str, datetime, bool], NodeRecovery],
) -> None:
    await repo.add(build_failure("A", now, True))
    await repo.add(build_failure("A", later, True))

    newest_recovery = await repo.get_newest_recovery_by_node_id("A")

    assert newest_recovery is not None
    assert newest_recovery.detected_at.replace(tzinfo=UTC) == later


async def test_get_newest_recovery_by_node_id_returns_none_when_the_node_has_no_row(
    repo: SqliteNodeRecoveryRepo,
) -> None:
    assert await repo.get_newest_recovery_by_node_id("A") is None


async def test_get_due_recoveries_returns_the_row_when_recover_at_is_the_given_time(
    repo: SqliteNodeRecoveryRepo,
    now: datetime,
    later: datetime,
    build_failure: Callable[[str, datetime, bool], NodeRecovery],
) -> None:
    await repo.add(build_failure("A", now, True))
    await repo.add(build_failure("B", later, True))

    due_recoveries = await repo.get_due_recoveries(now)

    assert [recovery.node_id for recovery in due_recoveries] == ["A"]


async def test_get_due_recoveries_skips_the_node_when_its_last_row_is_not_due(
    repo: SqliteNodeRecoveryRepo,
    now: datetime,
    later: datetime,
    build_failure: Callable[[str, datetime, bool], NodeRecovery],
) -> None:
    await repo.add(build_failure("A", now, True))
    await repo.add(build_failure("A", later, True))

    due_recoveries = await repo.get_due_recoveries(now)

    assert due_recoveries == []


async def test_get_due_recoveries_skips_the_row_when_it_is_not_recoverable(
    repo: SqliteNodeRecoveryRepo,
    now: datetime,
    later: datetime,
    build_failure: Callable[[str, datetime, bool], NodeRecovery],
) -> None:
    await repo.add(build_failure("A", now, False))

    due_recoveries = await repo.get_due_recoveries(later)

    assert due_recoveries == []


async def test_count_by_node_id_counts_only_that_node_when_several_nodes_have_rows(
    repo: SqliteNodeRecoveryRepo,
    now: datetime,
    later: datetime,
    build_failure: Callable[[str, datetime, bool], NodeRecovery],
) -> None:
    await repo.add(build_failure("A", now, True))
    await repo.add(build_failure("A", later, True))
    await repo.add(build_failure("B", now, True))

    assert await repo.count_by_node_id("A") == 2


async def test_count_by_node_id_returns_zero_when_the_node_has_no_row(
    repo: SqliteNodeRecoveryRepo,
) -> None:
    assert await repo.count_by_node_id("A") == 0
