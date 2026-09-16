from collections.abc import AsyncGenerator
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from virgo_agentic_dag.domain.persistence.entities.entity_base import EntityBase
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase

pytestmark = pytest.mark.integration


@pytest.fixture
def migrations_path() -> Traversable:
    return files("virgo_agentic_dag") / "migrations"


@pytest.fixture
def first_revision() -> str:
    return "a1c0d3f5e7b9"


@pytest.fixture
def agent_sessions_table_name() -> str:
    return "agent_sessions"


@pytest.fixture
def evidence_column_names() -> list[str]:
    return ["exit_code", "log_tail", "marks_before"]


@pytest.fixture
async def engine(tmp_path: Path) -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite3'}")

    yield engine

    await engine.dispose()


async def test_upgrade_to_head_creates_the_mapped_schema_when_the_database_is_empty(
    engine: AsyncEngine,
) -> None:
    database = SqliteDatabase(engine)

    await database.upgrade_to_head()

    async with engine.connect() as connection:
        migration_context = await connection.run_sync(MigrationContext.configure)
        differences = await connection.run_sync(
            lambda _: compare_metadata(migration_context, EntityBase.metadata)
        )

    assert differences == []


async def test_upgrade_to_head_adds_the_nullable_evidence_columns_when_the_database_is_at_the_first_revision(
    engine: AsyncEngine,
    migrations_path: Traversable,
    first_revision: str,
    agent_sessions_table_name: str,
    evidence_column_names: list[str],
) -> None:
    config = Config()
    config.set_main_option("script_location", str(migrations_path))
    async with engine.begin() as connection:
        config.attributes["connection"] = connection.sync_connection
        await connection.run_sync(lambda _: command.upgrade(config, first_revision))

    database = SqliteDatabase(engine)

    await database.upgrade_to_head()

    async with engine.connect() as connection:
        columns = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).get_columns(
                agent_sessions_table_name
            )
        )

    nullable_by_name = {column["name"]: column["nullable"] for column in columns}
    assert [nullable_by_name[name] for name in evidence_column_names] == [True] * 3
