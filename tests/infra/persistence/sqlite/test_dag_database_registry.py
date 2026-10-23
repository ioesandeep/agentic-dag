import asyncio
from collections.abc import Callable
from importlib.resources import files
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from virgo_agentic_dag.infra.locking.dag_run_lock import DagRunLock
from virgo_agentic_dag.infra.persistence.sqlite.dag_database_registry import (
    DagDatabaseRegistry,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def dag_home(tmp_path: Path, mocker: MockerFixture) -> Path:
    mocker.patch(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", return_value=tmp_path
    )

    return tmp_path


@pytest.fixture
def create_database_engine(dag_home: Path) -> Callable[[], AsyncEngine]:
    db_path = dag_home / "alpha" / "db.sqlite3"
    db_path.parent.mkdir()

    return lambda: create_async_engine(f"sqlite+aiosqlite:///{db_path}")


@pytest.fixture
def migrations_location() -> str:
    migrations_path = files("virgo_agentic_dag") / "migrations"

    return str(migrations_path)


async def test_registry_returns_no_gateway_when_the_dag_has_no_database(
    dag_home: Path,
) -> None:
    registry = DagDatabaseRegistry()
    dag_home.joinpath("alpha").mkdir()

    gateway = await registry.open("alpha")

    assert gateway is None


async def test_registry_returns_the_same_gateway_when_a_dag_opens_concurrently(
    dag_home: Path,
) -> None:
    registry = DagDatabaseRegistry()
    dag_home.joinpath("alpha").mkdir()
    dag_home.joinpath("alpha", "db.sqlite3").touch()

    first_open = registry.open("alpha")
    second_open = registry.open("alpha")
    first_gateway, second_gateway = await asyncio.gather(first_open, second_open)

    assert first_gateway is second_gateway

    await registry.dispose()


async def test_registry_opens_a_dag_again_when_it_has_been_disposed(
    dag_home: Path,
) -> None:
    registry = DagDatabaseRegistry()

    dag_home.joinpath("alpha").mkdir()
    dag_home.joinpath("alpha", "db.sqlite3").touch()

    first_gateway = await registry.open("alpha")

    await registry.dispose()

    reopened_gateway = await registry.open("alpha")

    assert reopened_gateway is not first_gateway

    await registry.dispose()


async def test_registry_migrates_an_older_database_before_opening_it(
    create_database_engine: Callable[[], AsyncEngine], migrations_location: str
) -> None:
    engine = create_database_engine()

    config = Config()
    config.set_main_option("script_location", migrations_location)
    async with engine.begin() as connection:
        config.attributes["connection"] = connection.sync_connection
        await connection.run_sync(lambda _: command.upgrade(config, "a1c0d3f5e7b9"))

    registry = DagDatabaseRegistry()

    try:
        gateway = await registry.open("alpha")

        assert gateway is not None

        nodes = await gateway.node_repo.get_all()
        async with engine.connect() as connection:
            columns = await connection.exec_driver_sql("PRAGMA table_info(work_trees)")
            column_names = {column.name for column in columns}

        assert nodes == []
        assert "pr_url" in column_names
    finally:
        await registry.dispose()
        await engine.dispose()


async def test_registry_opens_a_locked_run_without_migrating_it(
    dag_home: Path,
    create_database_engine: Callable[[], AsyncEngine],
    migrations_location: str,
) -> None:
    engine = create_database_engine()

    config = Config()
    config.set_main_option("script_location", migrations_location)
    async with engine.begin() as connection:
        config.attributes["connection"] = connection.sync_connection
        await connection.run_sync(lambda _: command.upgrade(config, "a1c0d3f5e7b9"))

    registry = DagDatabaseRegistry()
    run_lock = DagRunLock(dag_home / "alpha" / "db.sqlite3")
    run_lock.acquire()

    try:
        gateway = await registry.open("alpha")

        assert gateway is not None

        async with engine.connect() as connection:
            columns = await connection.exec_driver_sql("PRAGMA table_info(work_trees)")
            column_names = {column.name for column in columns}

        assert "pr_url" not in column_names
    finally:
        run_lock.release()
        await registry.dispose()
        await engine.dispose()
