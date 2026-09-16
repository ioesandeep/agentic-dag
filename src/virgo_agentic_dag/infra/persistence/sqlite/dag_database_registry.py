"""The registry of this host's dag databases."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import create_async_engine
from virgo_agentic_dag.infra.persistence.sqlite.dag_database_gateway import (
    DagDatabaseGateway,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase
from virgo_agentic_dag.utils.dag_utils import get_dag_db_path


class DagDatabaseRegistry:
    """The database gateway of any dag on this host."""

    def __init__(self) -> None:
        self._gateways: dict[str, DagDatabaseGateway] = {}

    def open(self, dag_name: str) -> DagDatabaseGateway | None:
        """Return this dag's gateway, or None when the dag keeps no database."""
        opened = self._gateways.get(dag_name)
        if opened is not None:
            return opened

        db_path = get_dag_db_path(dag_name)
        if not db_path.is_file():
            return None

        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        database = SqliteDatabase(engine)
        self._gateways[dag_name] = DagDatabaseGateway(database)

        return self._gateways[dag_name]

    async def dispose(self) -> None:
        """Close every database of this registry."""
        for gateway in self._gateways.values():
            await gateway.dispose()

        self._gateways.clear()
