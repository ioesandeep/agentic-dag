import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest

from virgo_agentic_dag.config.catalog_settings import CatalogSettings
from virgo_agentic_dag.domain.catalog.catalog_error import CatalogError
from virgo_agentic_dag.domain.catalog.catalog_error_code_enum import (
    CatalogErrorCodeEnum,
)
from virgo_agentic_dag.infra.workspace.managed_checkout_storage import (
    ManagedCheckoutStorage,
)

pytestmark = pytest.mark.integration

REPOSITORY_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
IMPORT_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


async def test_publication_preserves_checkout_contents_for_recovery(
    tmp_path: Path,
) -> None:
    catalog_settings = CatalogSettings(root=tmp_path)
    storage = ManagedCheckoutStorage(catalog_settings=catalog_settings)
    staging_path = await storage.create_staging(IMPORT_ID)
    checkout_file = staging_path / "README.md"
    checkout_file.write_text("checkout")
    missing_path = await storage.get_final_path(REPOSITORY_ID)

    final_path = await storage.publish_staging(REPOSITORY_ID, IMPORT_ID)
    recovered_path = await storage.get_final_path(REPOSITORY_ID)
    await storage.delete_staging(IMPORT_ID)

    expected_final_path = catalog_settings.get_repository_path(REPOSITORY_ID)
    assert final_path == expected_final_path
    assert missing_path is None
    assert recovered_path == final_path
    published_file = final_path / "README.md"
    assert published_file.read_text() == "checkout"
    assert not staging_path.exists()


@pytest.mark.parametrize("occupied_path", ["staging", "final"])
async def test_storage_preserves_existing_directories(
    tmp_path: Path, occupied_path: str
) -> None:
    catalog_settings = CatalogSettings(root=tmp_path)
    storage = ManagedCheckoutStorage(catalog_settings=catalog_settings)
    staging_path = await storage.create_staging(IMPORT_ID)
    staging_file = staging_path / "README.md"
    staging_file.write_text("checkout")
    final_path = catalog_settings.get_repository_path(REPOSITORY_ID)
    if occupied_path == "final":
        final_path.mkdir()

    with pytest.raises(CatalogError, match="cannot complete") as catalog_error:
        if occupied_path == "staging":
            await storage.create_staging(IMPORT_ID)
        else:
            await storage.publish_staging(REPOSITORY_ID, IMPORT_ID)

    assert catalog_error.value.code is CatalogErrorCodeEnum.PATH_CONFLICT
    assert staging_path.is_dir()
    assert staging_file.read_text() == "checkout"


@pytest.mark.parametrize("component", ["repositories", ".imports", "staging", "final"])
async def test_storage_rejects_symlink_paths(tmp_path: Path, component: str) -> None:
    catalog_root = tmp_path / "catalog"
    catalog_settings = CatalogSettings(root=catalog_root)
    storage = ManagedCheckoutStorage(catalog_settings=catalog_settings)
    external_path = tmp_path / "external"
    external_path.mkdir()
    paths = {
        "repositories": catalog_settings.repositories_path,
        ".imports": catalog_settings.imports_path,
        "staging": catalog_settings.get_import_path(IMPORT_ID),
        "final": catalog_settings.get_repository_path(REPOSITORY_ID),
    }
    symlink_path = paths[component]
    symlink_path.parent.mkdir(parents=True, exist_ok=True)
    symlink_path.symlink_to(external_path, target_is_directory=True)

    with pytest.raises(CatalogError, match="symlinks") as catalog_error:
        if component == "final":
            await storage.get_final_path(REPOSITORY_ID)
        else:
            await storage.delete_staging(IMPORT_ID)

    assert catalog_error.value.code is CatalogErrorCodeEnum.PATH_CONFLICT
    assert external_path.is_dir()


async def test_cleanup_preserves_other_attempts_and_external_files(
    tmp_path: Path,
) -> None:
    catalog_settings = CatalogSettings(root=tmp_path / "catalog")
    storage = ManagedCheckoutStorage(catalog_settings=catalog_settings)
    staging_path = await storage.create_staging(IMPORT_ID)
    other_staging_path = await storage.create_staging(
        "cccccccc-cccc-cccc-cccc-cccccccccccc"
    )
    external_path = tmp_path / "external"
    external_path.mkdir()
    external_file = external_path / "external.txt"
    external_file.write_text("uncommitted")
    staging_link = staging_path / "external"
    staging_link.symlink_to(external_path, target_is_directory=True)

    await storage.delete_staging(IMPORT_ID)

    assert not staging_path.exists()
    assert other_staging_path.is_dir()
    assert external_file.read_text() == "uncommitted"


async def test_staging_preserves_a_conflicting_run_directory(tmp_path: Path) -> None:
    catalog_settings = CatalogSettings(root=tmp_path)
    catalog_settings.repositories_path.mkdir()
    manifest_path = catalog_settings.repositories_path / "dag.toml"
    manifest_path.write_text("existing run")
    storage = ManagedCheckoutStorage(catalog_settings=catalog_settings)

    with pytest.raises(CatalogError, match="DAG manifest") as catalog_error:
        await storage.create_staging(IMPORT_ID)

    assert catalog_error.value.code is CatalogErrorCodeEnum.CATALOG_PATH_CONFLICT
    assert manifest_path.read_text() == "existing run"
    assert not catalog_settings.imports_path.exists()


async def test_cancellation_waits_for_pending_publication(tmp_path: Path) -> None:
    catalog_settings = CatalogSettings(root=tmp_path)
    storage = ManagedCheckoutStorage(catalog_settings=catalog_settings)
    await storage.create_staging(IMPORT_ID)
    event_loop = asyncio.get_running_loop()
    continue_thread = Event()
    with ThreadPoolExecutor(max_workers=1) as executor:
        event_loop.set_default_executor(executor)
        blocked_future = event_loop.run_in_executor(None, continue_thread.wait, 5)
        publication = storage.publish_staging(REPOSITORY_ID, IMPORT_ID)
        publication_task = asyncio.create_task(publication)
        await asyncio.sleep(0)

        publication_task.cancel()
        await asyncio.sleep(0)
        has_completed = publication_task.done()
        continue_thread.set()
        with pytest.raises(asyncio.CancelledError, match="^$"):
            await publication_task

        await blocked_future

    assert not has_completed
    final_path = catalog_settings.get_repository_path(REPOSITORY_ID)
    assert final_path.is_dir()
