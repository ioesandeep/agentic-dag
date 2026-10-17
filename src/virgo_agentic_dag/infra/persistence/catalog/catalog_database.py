import asyncio
from importlib.resources import files

from alembic import command
from alembic.config import Config
from sqlalchemy import URL, Connection, create_engine, event
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import ConnectionPoolEntry, NullPool

from virgo_agentic_dag.config.catalog_settings import CatalogSettings
from virgo_agentic_dag.domain.catalog.catalog_error import CatalogError
from virgo_agentic_dag.domain.catalog.catalog_error_code_enum import (
    CatalogErrorCodeEnum,
)
from virgo_agentic_dag.domain.catalog.ports.catalog_database import (
    CatalogDatabase as CatalogDatabasePort,
)
from virgo_agentic_dag.domain.infra.locking.run_lock import RunLock


class CatalogDatabase(CatalogDatabasePort):
    """Provide isolated catalog storage with explicit transaction commits."""

    def __init__(
        self, catalog_settings: CatalogSettings, migration_lock: RunLock
    ) -> None:
        self._catalog_settings = catalog_settings
        self._migration_lock = migration_lock
        database_path = str(catalog_settings.db_path)
        self._url = URL.create("sqlite", database=database_path)
        async_url = self._url.set(drivername="sqlite+aiosqlite")
        self._engine = create_async_engine(async_url)
        event.listen(self._engine.sync_engine, "connect", self._configure_connection)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    async def initialize(self) -> None:
        """Prepare catalog storage for use."""
        await asyncio.to_thread(self._initialize)

    def session(self) -> AsyncSession:
        """Open a catalog session whose caller owns the transaction."""
        return self._session_factory()

    async def dispose(self) -> None:
        """Release catalog database connections."""
        await self._engine.dispose()

    def _initialize(self) -> None:
        self._migration_lock.acquire_waiting()
        try:
            self._assert_storage_path()
            self._catalog_settings.imports_path.mkdir(parents=True, exist_ok=True)
            self._upgrade_to_head()
        finally:
            self._migration_lock.release()

    def _assert_storage_path(self) -> None:
        manifest_path = self._catalog_settings.repositories_path / "dag.toml"
        has_run_manifest = manifest_path.exists()
        if has_run_manifest:
            raise CatalogError(
                code=CatalogErrorCodeEnum.CATALOG_PATH_CONFLICT,
                detail="Catalog storage conflicts with an existing DAG run.",
            )

    def _upgrade_to_head(self) -> None:
        engine = create_engine(self._url, poolclass=NullPool)
        event.listen(engine, "connect", self._configure_connection)
        try:
            with engine.begin() as connection:
                self._run_migrations(connection)
        finally:
            engine.dispose()

    @staticmethod
    def _run_migrations(connection: Connection) -> None:
        migrations_path = files("virgo_agentic_dag") / "catalog_migrations"
        script_location = str(migrations_path)
        config = Config()
        config.set_main_option("script_location", script_location)
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

    @staticmethod
    def _configure_connection(
        connection: DBAPIConnection, _: ConnectionPoolEntry
    ) -> None:
        cursor = connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
        finally:
            cursor.close()
