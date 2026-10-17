import asyncio
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from virgo_agentic_dag.config.catalog_settings import CatalogSettings
from virgo_agentic_dag.domain.catalog.catalog_error import CatalogError
from virgo_agentic_dag.domain.catalog.catalog_error_code_enum import (
    CatalogErrorCodeEnum,
)
from virgo_agentic_dag.infra.locking.dag_run_lock import DagRunLock
from virgo_agentic_dag.infra.persistence.catalog.catalog_database import CatalogDatabase
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase

pytestmark = pytest.mark.integration


CATALOG_INITIALIZER_SCRIPT = """import asyncio
import sys
from pathlib import Path
from virgo_agentic_dag.config.catalog_settings import CatalogSettings
from virgo_agentic_dag.infra.locking.dag_run_lock import DagRunLock
from virgo_agentic_dag.infra.persistence.catalog.catalog_database import CatalogDatabase

root = Path(sys.argv[1])
settings = CatalogSettings(root=root)
run_lock = DagRunLock(settings.locks_path / "migrations")
database = CatalogDatabase(catalog_settings=settings, migration_lock=run_lock)
initialization = database.initialize()
asyncio.run(initialization)
"""


async def test_initializers_share_a_catalog_across_processes(tmp_path: Path) -> None:
    command = [sys.executable, "-c", CATALOG_INITIALIZER_SCRIPT, str(tmp_path)]
    first_initializer = asyncio.create_subprocess_exec(*command, stderr=subprocess.PIPE)
    second_initializer = asyncio.create_subprocess_exec(
        *command, stderr=subprocess.PIPE
    )

    processes = await asyncio.gather(first_initializer, second_initializer)
    completions = [process.communicate() for process in processes]
    outputs = await asyncio.gather(*completions)

    assert [process.returncode for process in processes] == [0, 0], outputs


async def test_connections_enforce_foreign_keys_and_busy_timeout(
    tmp_path: Path,
) -> None:
    settings = CatalogSettings(root=tmp_path)
    run_lock = DagRunLock(settings.locks_path / "migrations")
    database = CatalogDatabase(catalog_settings=settings, migration_lock=run_lock)
    await database.initialize()
    async with database.session() as session:
        parent = text("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        child = text("CREATE TABLE child (parent_id INTEGER REFERENCES parent(id))")
        await session.execute(parent)
        await session.execute(child)
        await session.commit()

    for _ in range(2):
        await database.dispose()
        async with database.session() as session:
            timeout = text("PRAGMA busy_timeout")
            timeout_result = await session.execute(timeout)
            assert timeout_result.scalar_one() == 5000
            invalid_child = text("INSERT INTO child VALUES (1)")
            with pytest.raises(IntegrityError, match="FOREIGN KEY constraint failed"):
                await session.execute(invalid_child)

    await database.dispose()


async def test_sessions_rollback_without_a_commit(tmp_path: Path) -> None:
    settings = CatalogSettings(root=tmp_path)
    run_lock = DagRunLock(settings.locks_path / "migrations")
    database = CatalogDatabase(catalog_settings=settings, migration_lock=run_lock)
    await database.initialize()
    async with database.session() as session:
        table = text("CREATE TABLE transaction_probe (id INTEGER PRIMARY KEY)")
        await session.execute(table)
        await session.commit()

    async with database.session() as session:
        insert = text("INSERT INTO transaction_probe VALUES (1)")
        await session.execute(insert)

    async with database.session() as session:
        count = text("SELECT COUNT(*) FROM transaction_probe")
        persisted_rows = await session.execute(count)

    await database.dispose()
    assert persisted_rows.scalar_one() == 0


async def test_catalog_initialization_preserves_run_storage(tmp_path: Path) -> None:
    manifest = tmp_path / "dag.toml"
    manifest.write_text('name = "existing"\n')
    run_path = tmp_path / "db.sqlite3"
    engine = create_async_engine(f"sqlite+aiosqlite:///{run_path}")
    run_database = SqliteDatabase(engine)
    await run_database.upgrade_to_head()
    await run_database.dispose()
    original_run = run_path.read_bytes()
    settings = CatalogSettings(root=tmp_path)
    run_lock = DagRunLock(settings.locks_path / "migrations")
    database = CatalogDatabase(catalog_settings=settings, migration_lock=run_lock)

    await database.initialize()

    async with database.session() as session:
        revisions = text("SELECT version_num FROM alembic_version")
        catalog_revisions = await session.execute(revisions)
        schema = text("SELECT name FROM sqlite_master WHERE type='table'")
        catalog_tables = await session.execute(schema)

    await database.dispose()
    catalog_table_rows = catalog_tables.all()
    catalog_table_set = set(catalog_table_rows)

    assert catalog_revisions.all() == [("c002",)]
    assert catalog_table_set == {("alembic_version",), ("projects",), ("repositories",)}
    assert run_path.read_bytes() == original_run
    assert manifest.read_text() == 'name = "existing"\n'


async def test_catalog_rejects_repositories_with_a_run_manifest(tmp_path: Path) -> None:
    settings = CatalogSettings(root=tmp_path)
    settings.repositories_path.mkdir()
    manifest = settings.repositories_path / "dag.toml"
    manifest.write_text('name = "repositories"\n')
    run_lock = DagRunLock(settings.locks_path / "migrations")
    database = CatalogDatabase(catalog_settings=settings, migration_lock=run_lock)

    with pytest.raises(CatalogError, match="existing DAG run") as failure:
        await database.initialize()

    await database.dispose()
    assert failure.value.code is CatalogErrorCodeEnum.CATALOG_PATH_CONFLICT
    assert manifest.read_text() == 'name = "repositories"\n'
    assert not settings.db_path.exists()
    assert not settings.imports_path.exists()
