import asyncio
import ctypes
import errno
import os
import shutil
import stat
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import partial
from pathlib import Path

from virgo_agentic_dag.config.catalog_settings import CatalogSettings
from virgo_agentic_dag.domain.catalog.catalog_error import CatalogError
from virgo_agentic_dag.domain.catalog.catalog_error_code_enum import (
    CatalogErrorCodeEnum,
)
from virgo_agentic_dag.domain.catalog.ports.managed_checkout_storage import (
    ManagedCheckoutStorage as ManagedCheckoutStoragePort,
)


class ManagedCheckoutStorage(ManagedCheckoutStoragePort):
    """Protect managed checkout directories during import publication and cleanup."""

    def __init__(self, catalog_settings: CatalogSettings) -> None:
        self._catalog_settings = catalog_settings

    async def create_staging(self, import_id: str) -> Path:
        """Allocate staging without replacing an existing attempt directory."""
        import_path = self._catalog_settings.get_import_path(import_id)

        return await self._execute_filesystem_operation(
            self._create_staging, import_path
        )

    async def publish_staging(self, repository_id: str, import_id: str) -> Path:
        """Publish caller-validated staging under the caller's repository lock."""
        repository_path = self._catalog_settings.get_repository_path(repository_id)
        import_path = self._catalog_settings.get_import_path(import_id)

        return await self._execute_filesystem_operation(
            self._publish_staging, repository_path, import_path
        )

    async def get_final_path(self, repository_id: str) -> Path | None:
        """Locate a final directory without validating its repository identity."""
        repository_path = self._catalog_settings.get_repository_path(repository_id)

        return await self._execute_filesystem_operation(
            self._get_final_path, repository_path
        )

    async def delete_staging(self, import_id: str) -> None:
        """Delete attempt staging after the caller confirms process termination."""
        import_path = self._catalog_settings.get_import_path(import_id)
        await self._execute_filesystem_operation(self._delete_staging, import_path)

    @staticmethod
    async def _execute_filesystem_operation[T](
        operation: Callable[..., T], *paths: Path
    ) -> T:
        event_loop = asyncio.get_running_loop()
        filesystem_call = partial(operation, *paths)
        filesystem_future = event_loop.run_in_executor(None, filesystem_call)
        is_cancelled = False
        while True:
            try:
                filesystem_result = await asyncio.shield(filesystem_future)
                break
            except asyncio.CancelledError:
                is_cancelled = True

        if is_cancelled:
            raise asyncio.CancelledError

        return filesystem_result

    def _create_staging(self, import_path: Path) -> Path:
        with self._translate_storage_errors(import_id=import_path.name):
            staging_path = self._get_contained_path(import_path)
            staging_path.parent.mkdir(parents=True, exist_ok=True)
            staging_path.mkdir()

            return staging_path

    def _publish_staging(self, repository_path: Path, import_path: Path) -> Path:
        with self._translate_storage_errors(repository_path.name, import_path.name):
            staging_path = self._get_contained_path(import_path)
            final_path = self._get_contained_path(repository_path)
            self._assert_directory(staging_path)
            self._rename_without_replacement(staging_path, final_path)

            return final_path

    def _get_final_path(self, repository_path: Path) -> Path | None:
        with self._translate_storage_errors(repository_id=repository_path.name):
            final_path = self._get_contained_path(repository_path)
            try:
                self._assert_directory(final_path)
            except FileNotFoundError:
                return None

            return final_path

    def _delete_staging(self, import_path: Path) -> None:
        with self._translate_storage_errors(import_id=import_path.name):
            staging_path = self._get_contained_path(import_path)
            try:
                shutil.rmtree(staging_path)
            except FileNotFoundError:
                return

    def _get_contained_path(self, catalog_path: Path) -> Path:
        catalog_root = self._catalog_settings.root.resolve()
        relative_path = catalog_path.relative_to(self._catalog_settings.root)
        contained_path = catalog_root
        for component in relative_path.parts:
            contained_path = contained_path / component
            is_symlink = contained_path.is_symlink()
            if is_symlink:
                raise CatalogError(
                    code=CatalogErrorCodeEnum.PATH_CONFLICT,
                    detail="Managed checkout paths must not contain symlinks.",
                    field="checkout_path",
                )

        manifest_path = catalog_root / "repositories" / "dag.toml"
        has_manifest = os.path.lexists(manifest_path)
        if has_manifest:
            raise CatalogError(
                code=CatalogErrorCodeEnum.CATALOG_PATH_CONFLICT,
                detail="The managed repository directory contains a DAG manifest.",
                field="checkout_path",
            )

        return contained_path

    @staticmethod
    def _assert_directory(checkout_path: Path) -> None:
        checkout_stat = checkout_path.stat()
        is_directory = stat.S_ISDIR(checkout_stat.st_mode)
        if not is_directory:
            raise CatalogError(
                code=CatalogErrorCodeEnum.CHECKOUT_INVALID,
                detail="The managed checkout path must be a directory.",
                field="checkout_path",
            )

    @staticmethod
    def _rename_without_replacement(staging_path: Path, final_path: Path) -> None:
        library = ctypes.CDLL(None, use_errno=True)
        encoded_staging_path = os.fsencode(staging_path)
        encoded_final_path = os.fsencode(final_path)
        if sys.platform == "darwin":
            rename_exclusive_flag = 4
            status = library.renamex_np(
                encoded_staging_path, encoded_final_path, rename_exclusive_flag
            )
        else:
            current_directory_descriptor = -100
            rename_no_replace_flag = 1
            status = library.renameat2(
                current_directory_descriptor,
                encoded_staging_path,
                current_directory_descriptor,
                encoded_final_path,
                rename_no_replace_flag,
            )

        if status != 0:
            error_number = ctypes.get_errno()
            error_message = os.strerror(error_number)

            raise OSError(error_number, error_message)

    @staticmethod
    @contextmanager
    def _translate_storage_errors(
        repository_id: str | None = None, import_id: str | None = None
    ) -> Iterator[None]:
        try:
            yield
        except OSError as error:
            error_code = CatalogErrorCodeEnum.IMPORT_FAILED
            if error.errno == errno.EEXIST:
                error_code = CatalogErrorCodeEnum.PATH_CONFLICT
            elif error.errno == errno.ENOENT:
                error_code = CatalogErrorCodeEnum.CHECKOUT_MISSING

            raise CatalogError(
                code=error_code,
                detail="The managed checkout storage operation cannot complete.",
                existing_repository_id=repository_id,
                import_id=import_id,
            ) from error
