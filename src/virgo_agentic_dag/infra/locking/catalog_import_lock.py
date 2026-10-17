import fcntl
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

from virgo_agentic_dag.config.catalog_settings import CatalogSettings
from virgo_agentic_dag.domain.catalog.catalog_error import CatalogError
from virgo_agentic_dag.domain.catalog.catalog_error_code_enum import (
    CatalogErrorCodeEnum,
)
from virgo_agentic_dag.domain.catalog.ports.catalog_import_lock import (
    CatalogImportLock as CatalogImportLockPort,
)


class CatalogImportLock(CatalogImportLockPort):
    """Keep repository imports exclusive across worker and clone processes."""

    def __init__(self, catalog_settings: CatalogSettings) -> None:
        self._catalog_settings = catalog_settings

    @contextmanager
    def acquire(self, repository_id: str) -> Iterator[int]:
        """Reserve a repository until every inherited descriptor closes."""
        repository_path = self._catalog_settings.get_repository_path(repository_id)
        lock_path = self._catalog_settings.locks_path / f"{repository_path.name}.lock"
        try:
            lock_file = self._open_locked_file(lock_path)
        except BlockingIOError as error:
            raise CatalogError(
                code=CatalogErrorCodeEnum.IMPORT_ACTIVE,
                detail="A repository import already owns the lock.",
                existing_repository_id=repository_path.name,
            ) from error
        except OSError as error:
            raise CatalogError(
                code=CatalogErrorCodeEnum.IMPORT_FAILED,
                detail="The repository import lock cannot be acquired.",
                existing_repository_id=repository_path.name,
            ) from error

        with lock_file:
            yield lock_file.fileno()

    @staticmethod
    def _open_locked_file(lock_path: Path) -> BinaryIO:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = lock_path.open("a+b")
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            lock_file.close()

            raise

        return lock_file
