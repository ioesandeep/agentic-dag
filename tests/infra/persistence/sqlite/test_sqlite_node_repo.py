from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_repo import SqliteNodeRepo

pytestmark = pytest.mark.integration

NOW = datetime(2026, 8, 9, tzinfo=UTC)

Settle = Callable[[str], Awaitable[None]]


@pytest.fixture
async def repo(tmp_path: Path) -> AsyncGenerator[SqliteNodeRepo]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite3'}")
    database = SqliteDatabase(engine)
    await database.upgrade_to_head()

    yield SqliteNodeRepo(database)

    await database.dispose()


@pytest.fixture
def settle(repo: SqliteNodeRepo) -> Settle:
    async def settle_node(node_id: str) -> None:
        node = await repo.read(node_id)
        assert node is not None

        await repo.record_pull_request_settled(node, NOW)

    return settle_node


async def test_ensure_rows_records_the_title_of_the_node_it_seeds(
    repo: SqliteNodeRepo,
) -> None:
    await repo.ensure_rows(
        [GraphNode(id="A", title="rename the token", name="Cancer")], NOW
    )

    row = await repo.read("A")
    assert row is not None and row.title == "rename the token"


async def test_ensure_rows_records_the_recovery_attempts_allowed_of_the_node_it_seeds(
    repo: SqliteNodeRepo,
) -> None:
    await repo.ensure_rows([GraphNode(id="A", recovery_attempts_allowed=5)], NOW)

    row = await repo.read("A")
    assert row is not None and row.recovery_attempts_allowed == 5


async def test_record_pull_request_settled_records_the_time_it_is_given(
    repo: SqliteNodeRepo,
) -> None:
    await repo.ensure_rows([GraphNode(id="A")], NOW)
    node = await repo.read("A")
    assert node is not None

    await repo.record_pull_request_settled(node, NOW)

    row = await repo.read("A")
    assert row is not None and row.pull_request_settled_at is not None
    assert row.pull_request_settled_at.replace(tzinfo=UTC) == NOW


async def test_get_nodes_due_for_learning_extraction_returns_the_node_when_its_pull_request_settled(
    repo: SqliteNodeRepo, settle: Settle
) -> None:
    await repo.ensure_rows([GraphNode(id="A"), GraphNode(id="B")], NOW)
    await settle("A")

    due_nodes = await repo.get_nodes_due_for_learning_extraction()
    assert [node.id for node in due_nodes] == ["A"]


async def test_get_nodes_due_for_learning_extraction_returns_nothing_when_the_learnings_are_extracted(
    repo: SqliteNodeRepo, settle: Settle
) -> None:
    await repo.ensure_rows([GraphNode(id="A")], NOW)
    await settle("A")

    due_nodes = await repo.get_nodes_due_for_learning_extraction()
    await repo.record_learnings_extracted(due_nodes, NOW)

    assert await repo.get_nodes_due_for_learning_extraction() == []


async def test_record_learnings_extracted_stamps_every_node_of_the_batch(
    repo: SqliteNodeRepo, settle: Settle
) -> None:
    await repo.ensure_rows([GraphNode(id="A"), GraphNode(id="B")], NOW)
    await settle("A")
    await settle("B")

    due_nodes = await repo.get_nodes_due_for_learning_extraction()
    await repo.record_learnings_extracted(due_nodes, NOW)

    rows = await repo.get_nodes_by_ids(["A", "B"])
    extracted_times = [
        row.learnings_extracted_at.replace(tzinfo=UTC)
        for row in rows
        if row.learnings_extracted_at is not None
    ]

    assert extracted_times == [NOW, NOW]
