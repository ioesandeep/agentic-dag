"""The registry of this host's dag databases."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine

from virgo_agentic_dag.domain.exceptions.run.run_busy import RunBusy
from virgo_agentic_dag.infra.locking.dag_run_lock import DagRunLock
from virgo_agentic_dag.infra.persistence.sqlite.dag_database_gateway import (
    DagDatabaseGateway,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase
from virgo_agentic_dag.utils.dag_utils import get_dag_db_path


class DagDatabaseRegistry:
    """The database gateway of any dag on this host."""

    def __init__(self) -> None:
        self._gateways: dict[str, DagDatabaseGateway] = {}
        self._open_lock = asyncio.Lock()

    async def open(self, dag_name: str) -> DagDatabaseGateway | None:
        """Return this dag's gateway, or None when the dag keeps no database."""
        async with self._open_lock:
            opened = self._gateways.get(dag_name)
            if opened is not None:
                return opened

            db_path = get_dag_db_path(dag_name)
            is_database_file = await asyncio.to_thread(db_path.is_file)
            if not is_database_file:
                return None

            database = await self._create_database(db_path)
            self._gateways[dag_name] = DagDatabaseGateway(database)

            return self._gateways[dag_name]

    async def _create_database(self, db_path: Path) -> SqliteDatabase:
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        database = SqliteDatabase(engine)
        try:
            async with self._acquire_run_lock(db_path) as is_run_lock_acquired:
                if is_run_lock_acquired:
                    await database.upgrade_to_head()
        except BaseException:
            await database.dispose()

            raise

        return database

    @asynccontextmanager
    async def _acquire_run_lock(self, db_path: Path) -> AsyncIterator[bool]:
        run_lock = DagRunLock(db_path)
        acquire_coroutine = asyncio.to_thread(run_lock.acquire)
        acquire_task = asyncio.create_task(acquire_coroutine)

        try:
            await asyncio.shield(acquire_task)
        except RunBusy:
            yield False
        else:
            yield True
        finally:
            with suppress(RunBusy):
                await acquire_task

            await self._release_run_lock(run_lock)

    async def _release_run_lock(self, run_lock: DagRunLock) -> None:
        release_coroutine = asyncio.to_thread(run_lock.release)
        release_task = asyncio.create_task(release_coroutine)
        try:
            await asyncio.shield(release_task)
        except asyncio.CancelledError:
            await release_task

            raise

    async def dispose(self) -> None:
        """Close every database of this registry."""
        for gateway in self._gateways.values():
            await gateway.dispose()

        self._gateways.clear()
